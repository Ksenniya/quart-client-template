Below is one possible refactored version of the file “entity/prototype.py”. In this version all direct interactions with the in‑memory dictionary (entity_jobs) have been replaced by calls to the external service (entity_service). In addition, the required startup code and the ENTITY_VERSION import have been added. (Note that if the external service does not support a particular operation, then that part is left as is.) 

─────────────────────────────────────────────

#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from dataclasses import dataclass
from quart import Quart, jsonify, request, abort
from quart_schema import QuartSchema, validate_request, validate_response  # Also use validate_querystring if needed
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
    companyName: str  # Required field, using only primitives

@dataclass
class JobResponse:
    jobId: str
    message: str

# NOTE: Previously we used an in‑memory dictionary (entity_jobs) to store job status and results.
# It is now completely replaced by external service calls via entity_service.

# Constants for external APIs
PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
# TODO: Provide actual URL or authentication details for the LEI lookup service.
LEI_API_BASE = "https://example.com/lei-lookup"  # Placeholder URL

async def fetch_companies(company_name: str) -> list:
    """Fetch companies from the Finnish Companies Registry API by company name."""
    params = {"name": company_name}
    async with aiohttp.ClientSession() as session:
        async with session.get(PRH_API_BASE, params=params) as resp:
            if resp.status != 200:
                # TODO: Improve error handling based on PRH API errors.
                return []
            data = await resp.json()
            # Assuming data format is similar to { "results": [ { company data }, ... ] }
            return data.get("results", [])  # Placeholder extraction

async def fetch_lei(company_info: dict) -> str:
    """Fetch LEI for a company using an external LEI lookup service."""
    # TODO: Replace this mock with a real API call.
    # For demonstration, assume if the length of companyName is even, an LEI is found.
    if len(company_info.get("companyName", "")) % 2 == 0:
        return "MOCK-LEI-1234567890"
    return "Not Available"

async def process_entity(job_id: str, search_payload: dict):
    """Process the company search: fetch companies, filter and enrich with LEI."""
    # Record the current time as the request time.
    requested_at = datetime.datetime.utcnow().isoformat()
    # Update the job record with the requestedAt timestamp.
    initial_update = {"requestedAt": requested_at}
    entity_service.update_item(
        token=cyoda_token,
        entity_model=ENTITY_MODEL,
        entity_version=ENTITY_VERSION,
        entity=initial_update,
        meta={"technical_id": job_id}
    )
    
    # 1. Fetch companies from PRH API
    company_name = search_payload.get("companyName", "")
    companies = await fetch_companies(company_name)

    # 2. Filter out inactive companies.
    # TODO: Verify the actual key and values indicating active status.
    active_companies = [
        company for company in companies
        if company.get("status", "").lower() == "active"
    ]

    # 3. For each active company, lookup the LEI.
    results = []
    for company in active_companies:
        lei = await fetch_lei(company)
        enriched = {
            "companyName": company.get("companyName", "N/A"),
            "businessId": company.get("businessId", "N/A"),
            "companyType": company.get("companyType", "N/A"),
            "registrationDate": company.get("registrationDate", "N/A"),
            "status": "Active",  # We filtered out inactive companies already
            "lei": lei,
        }
        results.append(enriched)

    # 4. Update the job record with the completed results.
    final_update = {
        "results": results,
        "status": "completed"
    }
    entity_service.update_item(
        token=cyoda_token,
        entity_model=ENTITY_MODEL,
        entity_version=ENTITY_VERSION,
        entity=final_update,
        meta={"technical_id": job_id}
    )

# POST endpoint: all external fetching, filtering, enrichment are done here.
# Workaround: For POST endpoints, the route decorator must be first,
# then validate_request and validate_response, as per quart-schema known issue.
@app.route("/api/companies/search", methods=["POST"])
@validate_request(CompanySearchRequest)  # This decorator must follow the route decorator.
@validate_response(JobResponse, 201)
async def search_companies(data: CompanySearchRequest):
    # The validated payload is received as 'data'
    # Create an initial job record with status "processing" and no results.
    initial_data = {"status": "processing", "requestedAt": None, "results": None}
    # Instead of using a local in‑memory cache we now add the item via entity_service.
    job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model=ENTITY_MODEL,
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=initial_data  # the validated data object
    )
    
    # Fire-and-forget the processing task.
    # TODO: Consider logging or exception handling for background tasks.
    asyncio.create_task(process_entity(job_id, data.__dict__))

    # Return the job id so that client can poll for results.
    return jsonify({
        "jobId": job_id,
        "message": "Search initiated. Use jobId to poll for results."
    }), 201

# GET endpoint: used for retrieving results via job_id.
# Since GET requests do not contain a body, no validation decorators are needed.
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

    # If processing is still underway, indicate that.
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

─────────────────────────────────────────────

Notes on the changes:
1. All persistence operations (creation, update, retrieval) now use the external service’s functions:
   • In the POST endpoint, an initial job record is created by calling entity_service.add_item.
   • In process_entity the job record is updated (first with the “requestedAt” timestamp then with the processing “results” and status) using entity_service.update_item.
   • In the GET endpoint, the job record is fetched using entity_service.get_item.
2. The previously used in-memory storage (entity_jobs) has been entirely removed.
3. The constant ENTITY_MODEL is defined as "companies_search" (feel free to change this value if a different entity name is required).
4. The startup code initializes the cyoda service as required.
5. All the external API calls and business logic (data ingestion, filtering, enrichment, etc.) are preserved.

This should meet the refactoring requirements.