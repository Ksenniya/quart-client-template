Below is one possible refactored version of the prototype code. In this version all direct uses of the local in‑memory cache (the entity_jobs dictionary) are replaced by calls to the external service functions (entity_service.add_item, get_item, update_item, etc.) Note that the entity_model used in all these calls is set to "companies" (replace with your actual entity name as needed) and the constant ENTITY_VERSION is always imported and used. We also add the startup hook to initialize cyoda as requested. (If additional external service calls are needed but not available, we leave the business‐logic as is.) 

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
    # TODO: Add additional filter fields if needed (must be primitives)

@dataclass
class SearchResponse:
    searchId: str
    status: str
    message: str

# External endpoints (local cache replaced via external service calls)
PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3"
LEI_API_URL = "https://mock-lei-service.example.com/getLei"  # TODO: Replace with an official endpoint

async def fetch_companies_from_prh(company_name, filters):
    """
    Query PRH API for companies.
    """
    params = {"name": company_name}
    # TODO: Map additional filters to the query parameters if needed.
    import aiohttp  # local import to avoid top‑level dependency issues
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

async def process_entity(job_id, payload):
    """
    Background task to process company search and enrichment.
    Instead of updating an in‑memory dictionary entry, we update the job record
    via entity_service.update_item.
    """
    try:
        company_name = payload.get("companyName")
        filters = payload.get("filters", {})  # Currently unused; TODO: enhance filter mapping if needed

        # 1. Retrieve companies from PRH API
        companies = await fetch_companies_from_prh(company_name, filters)

        # 2. Filter out inactive companies
        active_companies = [company for company in companies if is_company_active(company)]

        # 3. Enrich each active company with LEI information
        enriched_companies = []
        for company in active_companies:
            lei = await fetch_lei_for_company(company)
            enriched_company = {
                "companyName": company.get("companyName", "Unknown"),   # TODO: Adjust key names per PRH response
                "businessId": company.get("businessId", "Unknown"),         # TODO: Adjust accordingly
                "companyType": company.get("companyType", "Unknown"),       # TODO: Adjust accordingly
                "registrationDate": company.get("registrationDate", "Unknown"),  # TODO: Adjust accordingly
                "status": "Active",
                "LEI": lei
            }
            enriched_companies.append(enriched_company)

        # 4. Build updated job data and update it via the external service.
        updated_job = {
            "searchId": job_id,
            "status": "completed",
            "requestedAt": payload.get("requestedAt"),  # preserve original request time if available
            "completedAt": datetime.datetime.utcnow().isoformat(),
            "results": enriched_companies
        }
        entity_service.update_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            entity=updated_job,
            meta={}
        )
    except Exception as e:
        # In case of error, update the job record with error status.
        error_job = {
            "searchId": job_id,
            "status": "error",
            "error": str(e)
        }
        entity_service.update_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            entity=error_job,
            meta={}
        )
        # TODO: Optionally log the error.

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
    # (Optionally, add the current timestamp to the payload so the background task has it available.)
    payload["requestedAt"] = datetime.datetime.utcnow().isoformat()

    # Generate a unique search id.
    search_id = str(uuid.uuid4())

    # Create the initial job record.
    job_record = {
        "searchId": search_id,
        "status": "processing",
        "requestedAt": payload["requestedAt"],
        "results": None
    }

    # Save the job record via external entity_service.
    id_returned = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        entity=job_record
    )

    # Fire‑and‑forget background task to process the search.
    asyncio.create_task(process_entity(search_id, payload))

    return SearchResponse(
        searchId=id_returned,  # return the id from the external service so the client can query later
        status="processing",
        message="Your search is being processed."
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

Explanation of key changes:

1. All local in‑memory storage (the entity_jobs dictionary) has been removed. Instead, we save and update job records using:
   • entity_service.add_item for the POST (search) endpoint (this call returns an id that we include in the response).
   • entity_service.update_item inside the background processing function to update job records (with enriched company data, completedAt, etc.).
   • entity_service.get_item on the GET endpoint to retrieve job records.

2. The startup function now initializes the cyoda repository using init_cyoda(cyoda_token).

3. The API endpoints themselves (routes and validations) remain unchanged from a business logic perspective; only the caching layer has been replaced.

4. TODO comments remain to indicate where additional logic, mapping, error‑handling, or production API endpoints might be needed.

Make sure that entity_service’s implementation supports these functions (and that its API is asynchronous if required). Adjust the "entity_model" string as needed if your design calls for a different entity identifier.