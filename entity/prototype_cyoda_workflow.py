Below is one complete updated version of the code. In this revision we assume that new entity_service.add_item now expects an extra keyword argument (workflow) that is an asynchronous function invoked on the entity “job record” before it is persisted. In the updated implementation the search job record is built with the search parameters (so that the workflow function can “see” which companies to search for), and the workflow function (named process_companies) is provided as a parameter. This workflow function takes the job record (a dictionary) as its only argument, performs the search operations (calling the external PRH API, filtering active companies, enriching each with LEI information), and then revises the entity state before it is finally persisted.

Below is the full code:

------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from dataclasses import dataclass

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response

# Import external service functions and constants
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Initialize quart-schema

# Startup hook to initialize cyoda
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Dataclasses for request/response validation
@dataclass
class CompanySearchRequest:
    companyName: str
    # Optionally, add additional filter fields if needed (must be primitives)
    filters: dict = None

@dataclass
class SearchResponse:
    searchId: str
    status: str
    message: str

# External endpoints (the local in‑memory cache is now replaced by external service calls)
PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3"
LEI_API_URL = "https://mock-lei-service.example.com/getLei"  # TODO: Replace with an official endpoint

async def fetch_companies_from_prh(company_name, filters):
    """
    Query PRH API for companies.
    """
    params = {"name": company_name}
    # TODO: Map additional filters to the query parameters if needed.
    import aiohttp  # local import to avoid top-level dependency issues
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{PRH_API_BASE}/companies", params=params) as response:
            if response.status == 200:
                data = await response.json()
                # TODO: Adjust based on actual API response structure.
                return data.get("results", [])
            else:
                # TODO: Handle/log errors appropriately.
                return []

async def fetch_lei_for_company(company):
    """
    Mock function to retrieve the LEI for a company.
    In a real implementation, this should call an official LEI registry.
    """
    # TODO: Replace this mock with actual logic to query the LEI service.
    await asyncio.sleep(0.2)  # Simulate network delay
    # For demonstration, companies with an even‑length name get a valid LEI.
    if len(company.get("companyName", "")) % 2 == 0:
        return "VALID_LEI_MOCK"
    else:
        return "Not Available"

def is_company_active(company):
    """
    Determine whether a company is active.
    Assumes that the company data has a "status" key with value "Active" if active.
    TODO: Adjust logic based on actual data.
    """
    return company.get("status", "").lower() == "active"

# New workflow function to process the "companies" entity before it is finally persisted.
# This function is applied by entity_service.add_item on the job record.
async def process_companies(entity):
    """
    Process the search job: performs the company search and enrichment and then updates
    the job state inside the entity. This function takes the job record (entity dict) as its only argument.
    
    NOTE:
    • Do not add/update/delete an entity from the same entity_model ("companies")
      inside this function as it might cause infinite recursion.
    • Instead, update the state in the entity and return the modified entity.
    """
    try:
        # Extract search parameters that were stored in the job record.
        company_name = entity.get("companyName")
        filters = entity.get("filters", {})
        
        # 1. Retrieve companies from PRH API
        companies = await fetch_companies_from_prh(company_name, filters)
        
        # 2. Filter out inactive companies
        active_companies = [company for company in companies if is_company_active(company)]
        
        # 3. Enrich each active company with LEI information
        enriched_companies = []
        for company in active_companies:
            lei = await fetch_lei_for_company(company)
            enriched_company = {
                "companyName": company.get("companyName", "Unknown"),   # adjust key names per PRH response as necessary
                "businessId": company.get("businessId", "Unknown"),
                "companyType": company.get("companyType", "Unknown"),
                "registrationDate": company.get("registrationDate", "Unknown"),
                "status": "Active",
                "LEI": lei
            }
            enriched_companies.append(enriched_company)
        
        # 4. Update the entity state with the search results
        entity["status"] = "completed"
        entity["completedAt"] = datetime.datetime.utcnow().isoformat()
        entity["results"] = enriched_companies
        
    except Exception as e:
        # In case of error update the state of the job record.
        entity["status"] = "error"
        entity["error"] = str(e)
    
    # Return the (possibly modified) entity so that the external service persists it.
    return entity

# POST endpoint: route first, then validation decorators (workaround for quart‑schema issue)
@app.route("/companies/search", methods=["POST"])
@validate_request(CompanySearchRequest)  # Must be second in POST endpoints
@validate_response(SearchResponse, 200)
async def search_companies(data: CompanySearchRequest):
    """
    Triggers the company search and enrichment process.
    Expects a JSON body with at least a companyName.
    """
    payload = data.__dict__
    # Store current timestamp so the workflow function has it available.
    current_time = datetime.datetime.utcnow().isoformat()
    
    # Generate a unique search id.
    search_id = str(uuid.uuid4())
    
    # Create the initial job record.
    # Note: We now include the search parameters in the record (e.g. companyName, filters)
    # so that the workflow function can later execute the search.
    job_record = {
        "searchId": search_id,
        "status": "processing",
        "requestedAt": current_time,
        "results": None,
        "companyName": payload.get("companyName"),
        "filters": payload.get("filters", {})
    }
    
    # Save the job record via the external entity_service.
    # The new workflow function "process_companies" will be applied asynchronously
    # to the job record before it is persisted.
    id_returned = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_record,              # the initial job record with search parameters
        workflow=process_companies      # workflow function applied asynchronously before persistence
    )
    
    # Return the search id immediately so the client can later query for results.
    return SearchResponse(
        searchId=id_returned,  # id returned from entity_service
        status="processing",
        message="Your search has been received and is being processed."
    )

# GET endpoint for results retrieval.
@app.route("/companies/results/<job_id>", methods=["GET"])
async def get_search_results(job_id):
    """
    Retrieves search results for a given search job identifier.
    """
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        return jsonify({"error": "Invalid searchId"}), 404

    if job.get("status") == "processing":
        return jsonify({
            "searchId": job_id,
            "status": "processing",
            "message": "Your search is still being processed, please try again later."
        })

    if job.get("status") == "error":
        return jsonify({
            "searchId": job_id,
            "status": "error",
            "message": "There was an error processing your search.",
            "error": job.get("error")
        })

    results = job.get("results", [])
    return jsonify({
        "searchId": job_id,
        "results": results,
        "metadata": {
            "requestedAt": job.get("requestedAt"),
            "completedAt": job.get("completedAt"),
            "resultCount": len(results)
        }
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
------------------------------------------------

Explanation of the main changes:
1. In the POST endpoint, the call to entity_service.add_item now includes the extra parameter workflow=process_companies. This provides an asynchronous “hook” that runs on the job record before it is persisted.
2. The newly implemented workflow function (process_companies) takes the job record (entity) as its only argument, extracts the search parameters (companyName and filters), fetches and filters companies from the external PRH API, enriches them with LEI information, and updates the job state (status, completedAt, results). In the event of an error, it sets the status to "error" and stores the error message.
3. The GET endpoint remains the same, reading the (possibly updated) job record from the external repository.

This complete revision removes the previous manual background task scheduling and now relies on the workflow function provided to entity_service.add_item to process the entity asynchronously before final persistence.