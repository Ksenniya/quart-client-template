Yes, absolutely. In our current setup the endpoint is doing some heavy lifting by firing off an async task to process the data. By moving that logic into the workflow function (process_{entity_name}) we simplify our controller code and encapsulate all asynchronous business logic where it belongs. This approach has several benefits:

1. Cleaner Controllers. The endpoint now only creates the initial entity record and returns a job ID. It doesn’t carry the weight of asynchronous processing logic.
2. Robust Asynchronous Logic. Since the workflow function supports asynchronous code and runs immediately before persistence, it’s the perfect place for fetching external data, filtering, enriching, and even triggering supplementary operations.
3. Better Separation of Concerns. The workflow function can modify the entity’s state directly (e.g. entity['attribute'] = new_value), while the controller remains free of side effects.
4. Avoiding Infinite Recursion. Since we no longer call entity_service.add/update/delete on the current entity in the workflow function, we prevent potential recursion problems.

Below is a complete refactored code example that shows how all the logic previously contained in a fire‐and‐forget async task can be moved into the workflow function.

──────────────────────────────
#!/usr/bin/env python3
import asyncio
import datetime
from dataclasses import dataclass
from quart import Quart, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response
import aiohttp

# New imports for external service usage
from common.config.config import ENTITY_VERSION
from app_init.app_init import cyoda_token, entity_service
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # single-line integration per requirements

# Startup hook for initializing cyoda as required
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Define the entity_model name for this module (used in all entity_service calls)
ENTITY_MODEL = "companies_search"

# Dataclasses for validation
@dataclass
class CompanySearchRequest:
    companyName: str  # Required field

@dataclass
class JobResponse:
    jobId: str
    message: str

# Constants for external APIs
PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
LEI_API_BASE = "https://example.com/lei-lookup"  # Placeholder URL

async def fetch_companies(company_name: str) -> list:
    """
    Fetch companies from the Finnish Companies Registry API by company name.
    """
    params = {"name": company_name}
    async with aiohttp.ClientSession() as session:
        async with session.get(PRH_API_BASE, params=params) as resp:
            if resp.status != 200:
                # TODO: Improve error handling based on PRH API errors.
                return []
            data = await resp.json()
            # Assuming data format is similar to { "results": [ { company data }, ... ] }
            return data.get("results", [])

async def fetch_lei(company_info: dict) -> str:
    """
    Fetch LEI using an external LEI lookup service.
    """
    # For demonstration, assume if the length of companyName is even, an LEI is found.
    if len(company_info.get("companyName", "")) % 2 == 0:
        return "MOCK-LEI-1234567890"
    return "Not Available"

async def process_companies_search(entity: dict) -> dict:
    """
    Workflow function applied to the job entity before persistence.

    This function updates the job's state: it timestamps the request, fetches companies,
    filters and enriches them, and then updates the status. Any asynchronous processing
    that was previously handled by fire-and-forget tasks is now handled here.
    
    NOTE: Do NOT invoke entity_service.add/update/delete on the current entity.
    Simply modify the 'entity' dictionary directly.
    """
    # Add the requestedAt timestamp directly to the entity
    entity["requestedAt"] = datetime.datetime.utcnow().isoformat()

    # Retrieve the search payload stored as 'query'
    search_payload = entity.get("query", {})
    company_name = search_payload.get("companyName", "")

    # 1. Fetch companies from the PRH API
    companies = await fetch_companies(company_name)

    # 2. Filter out inactive companies (assuming only those with status "active")
    active_companies = [
        company for company in companies
        if company.get("status", "").lower() == "active"
    ]

    # 3. Enrich each active company by fetching its LEI
    results = []
    for company in active_companies:
        lei = await fetch_lei(company)
        enriched = {
            "companyName": company.get("companyName", "N/A"),
            "businessId": company.get("businessId", "N/A"),
            "companyType": company.get("companyType", "N/A"),
            "registrationDate": company.get("registrationDate", "N/A"),
            "status": "Active",  # already filtered
            "lei": lei
        }
        results.append(enriched)

    # 4. Update the entity with the results and mark it completed
    entity["results"] = results
    entity["status"] = "completed"
    return entity

# POST endpoint: we now simply create the job record and let the workflow function process it.
@app.route("/api/companies/search", methods=["POST"])
@validate_request(CompanySearchRequest)
@validate_response(JobResponse, 201)
async def search_companies(data: CompanySearchRequest):
    # Prepare the initial entity to be stored
    initial_data = {
        "status": "processing",
        "requestedAt": None,
        "results": None,
        "query": data.__dict__   # store the search parameters for processing
    }

    # Create job record through entity_service.add_item
    # The workflow function is passed here as the 'workflow' parameter.
    job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model=ENTITY_MODEL,
        entity_version=ENTITY_VERSION,
        entity=initial_data,
        workflow=process_companies_search  # workflow function that processes the record
    )

    # Immediately return the job id; the workflow will process the entity asynchronously before persistence.
    return jsonify({
        "jobId": job_id,
        "message": "Search initiated. Use jobId to poll for results."
    }), 201

# GET endpoint: used for retrieving job results.
@app.route("/api/companies/<job_id>", methods=["GET"])
async def get_search_results(job_id):
    # Retrieve the job record from the external service.
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model=ENTITY_MODEL,
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        abort(404, description="Job not found")

    # If processing is still underway, let the user know.
    if job.get("status") != "completed":
        return jsonify({
            "jobId": job_id,
            "status": job.get("status"),
            "message": "Processing. Please check back later."
        })

    # Return the completed results.
    return jsonify({
        "jobId": job_id,
        "completed": True,
        "results": job.get("results", [])
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
──────────────────────────────

In this refactoring:

• The endpoint (controller) no longer handles details about API calls or data processing.
• The workflow function process_companies_search handles all asynchronous operations (data fetching, filtering, LEI enrichment) and directly updates the in–memory state of the entity.
• We avoid using fire-and-forget patterns within the endpoint, replacing that with our dedicated workflow that runs asynchronously before the entity is persisted.

This results in a simpler, more robust, and decoupled architecture for our service.