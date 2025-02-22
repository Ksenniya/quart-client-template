Below is one example of how you could refactor the code so that the controller (endpoint) is “skin‐ny” by moving the heavy lifting into the workflow function. In this example we completely remove the fire‐and‐forget process_entity task and instead define an asynchronous workflow function (process_companies) that performs all the enrichment steps (calling external APIs, filtering companies, fetching LEI data) before the entity is persisted. (Remember that the workflow function operates on the entity “by reference” so any changes you make to it will be persisted.) 

The main differences are:

1. The POST endpoint now only creates a “job” object (with minimal “processing” state information) and calls entity_service.add_item with the workflow function.  
2. The process_companies workflow function does all asynchronous external calls (to the Finnish Companies Registry API, or LEI enrichment) and then modifies the job’s entity fields (for example, setting “results” and “status”) before persistence.  
3. Since the workflow function supports asynchronous code, you no longer need to fire‐and‐forget a separate task.  

Below is a complete updated code sample:

------------------------------------------------------------
#!/usr/bin/env python3
import asyncio
import datetime
import aiohttp

from dataclasses import dataclass
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response

# New imports for external entity persistence and cyoda startup.
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

# Add startup initialization to set up cyoda:
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Define data classes for request/response objects

@dataclass
class CompanySearchRequest:
    companyName: str
    registrationDateFrom: str = ""
    registrationDateTo: str = ""

@dataclass
class CompanyRecord:
    companyName: str
    businessId: str
    companyType: str
    registrationDate: str
    status: str
    lei: str

@dataclass
class CompanySearchResponse:
    searchId: str
    results: list  # A list of CompanyRecord (primitive based) dictionaries

# Asynchronous function to call the Finnish Companies Registry API
async def fetch_prh_data(company_name: str) -> dict:
    """Calls the Finnish Companies Registry API and returns JSON data."""
    prh_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
    params = {"name": company_name}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(prh_url, params=params) as resp:
                if resp.status != 200:
                    # Returning empty results on error in this prototype.
                    return {}
                data = await resp.json()
                return data
        except Exception as e:
            # TODO: Log actual error
            return {}

# Asynchronous function to fetch the LEI data.
async def fetch_lei_data(company: dict) -> str:
    """
    Fetches the LEI for a given company using an external LEI API.
    In this placeholder, if the last digit of the businessId is even we return a sample LEI.
    """
    await asyncio.sleep(0.1)  # simulate network delay
    try:
        if int(company.get("businessId", "0")[-1]) % 2 == 0:
            return "5493001KJTIIGC8Y1R12"
    except Exception:
        pass
    return "Not Available"

# Workflow function that is applied asynchronously before persisting the entity.
# This function replaces the previous fire-and-forget task.
async def process_companies(entity: dict):
    """
    Enrich the companies entity before it is persisted.
    This function is invoked asynchronously during the add_item operation.
    Note: Only modify the given entity data. Do not call add/update/delete on the same model.
    """
    # The entity at this point is the job record created by the controller.
    # Read company name saved from the incoming request data.
    company_name = entity.get("companyName")
    if not company_name:
        # If no company name, mark the job as failed.
        entity["status"] = "failed"
        entity["error"] = "Missing companyName"
        return entity

    # Begin enrichment: fetch company data from the Finnish Companies Registry API.
    prh_response = await fetch_prh_data(company_name)
    companies = prh_response.get("results", []) if prh_response else []

    # Filter to include only active companies.
    active_companies = [c for c in companies if c.get("status", "").lower() == "active"]

    # Enrich each active company with LEI data.
    results = []
    for company in active_companies:
        lei = await fetch_lei_data(company)
        enriched = {
            "companyName": company.get("companyName", "Unknown"),
            "businessId": company.get("businessId", "Unknown"),
            "companyType": company.get("companyType", "Unknown"),
            "registrationDate": company.get("registrationDate", "Unknown"),
            "status": "Active",
            "lei": lei
        }
        results.append(enriched)
    
    # Update the entity directly.
    entity["results"] = results
    entity["status"] = "completed"
    entity["workflowProcessedAt"] = datetime.datetime.utcnow().isoformat() + "Z"

    # Optionally you could add supplementary or raw data of any other entity_model if needed.
    return entity

# POST endpoint: minimal controller logic
@app.route("/companies/search", methods=["POST"])
@validate_request(CompanySearchRequest)
@validate_response(CompanySearchResponse, 200)
async def search_companies(data: CompanySearchRequest):
    """Initiate a company search. The heavy lifting is done inside the workflow function."""
    if not data.companyName:
        abort(400, description="Missing required field: companyName")
    
    # Create a job entity with the basic information
    requested_at = datetime.datetime.utcnow().isoformat() + "Z"
    job_data = {
        "companyName": data.companyName,
        "status": "processing",
        "requestedAt": requested_at,
        "results": []
    }
    
    # Persist the job using the external repository.
    # The workflow function process_companies will be applied asynchronously
    # before the entity is finally persisted.
    job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_data,
        workflow=process_companies  # Workflow function replaces fire-and-forget async tasks.
    )
    
    # Immediately return a response with the job id.
    return CompanySearchResponse(searchId=job_id, results=[])

# GET endpoint: Retrieve processed search results.
@app.route("/companies/results/<job_id>", methods=["GET"])
async def get_results(job_id):
    """Retrieve stored enriched results using the job's search id."""
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        abort(404, description="Job ID not found.")
    
    # Return the stored job result.
    response = {
        "searchId": job_id,
        "results": job.get("results"),
        "status": job.get("status"),
        "requestedAt": job.get("requestedAt")
    }
    return jsonify(response)

# Test endpoint for checking service health.
@app.route("/", methods=["GET"])
async def index():
    return "Finnish Companies Data Retrieval and Enrichment Prototype is running."

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
------------------------------------------------------------

Key points in this refactored design:

• The controller (search_companies) is very simple: it validates input, creates a minimal job entity, and calls entity_service.add_item with the workflow function.  
• The entire asynchronous business logic (external API calls, filtering, enrichment) is inside process_companies. Since the workflow function is invoked right before the entity is persisted, the updated state (e.g. enriched results, status “completed”) is saved.  
• By placing the enrichment logic in the workflow function you “free” your controllers from excessive logic and you have a single place to change effects related to asynchronous processing of the entity.  
• Finally, note the constraint: you are not allowed to call entity_service.add/update/delete on the same entity within the workflow; you must modify its fields directly.

This approach makes the design more robust and easier to maintain.