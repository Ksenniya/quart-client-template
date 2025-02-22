Below is one possible refactored version of your prototype (companies) module. In this update the in‑memory dictionary (entity_jobs) is removed, and all writes/reads for the “job” are done via calls to the external service (entity_service) using only the allowed functions. In addition the new startup code (importing ENTITY_VERSION, initializing cyoda) has been added. The business logic for processing, enrichment, external API calls, etc. is left intact.

──────────────────────────── updated prototype.py ─────────────────────────────
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
import aiohttp

from dataclasses import dataclass
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response  # for GET, use validate_querystring if needed

# New imports for external entity persistence and cyoda startup.
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

# Remove local in‑memory persistence (entity_jobs) entirely.

# Add startup initialization to set up cyoda:
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Define data classes for request/response objects

@dataclass
class CompanySearchRequest:
    companyName: str
    # Optional fields for future expansion (only primitives)
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
    results: list  # List of CompanyRecord objects (using only primitives)

# Asynchronous function to call the Finnish Companies Registry API
async def fetch_prh_data(company_name: str) -> dict:
    """Calls the Finnish Companies Registry API and returns JSON data."""
    prh_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
    params = {"name": company_name}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(prh_url, params=params) as resp:
                if resp.status != 200:
                    # TODO: Add proper error handling and logging if needed.
                    return {}  # Return empty dict on error for prototype
                data = await resp.json()
                return data
        except Exception as e:
            # TODO: Log the exception properly.
            return {}

# Asynchronous function to fetch the LEI data.
async def fetch_lei_data(company: dict) -> str:
    """Fetches the LEI for a given company using an external LEI API.
       This is a placeholder that simulates the LEI lookup.
    """
    # TODO: Replace with actual LEI data source call when available.
    await asyncio.sleep(0.1)  # simulate network delay
    try:
        if int(company.get("businessId", "0")[-1]) % 2 == 0:
            return "5493001KJTIIGC8Y1R12"
    except Exception:
        pass
    return "Not Available"

# Asynchronous processing function that retrieves, filters, and enriches company data.
# Instead of updating local cache, we update the entity via entity_service.update_item.
async def process_entity(job_id: str, input_data: dict):
    """Process the retrieval, filtering, and LEI enrichment.
       This function is executed asynchronously after accepting a job.
    """
    results = []
    company_name = input_data.get("companyName")

    # Call the Finnish Companies Registry API.
    prh_response = await fetch_prh_data(company_name)

    # TODO: Adjust below based on real API response structure.
    companies = prh_response.get("results", []) if prh_response else []

    # Filtering out inactive companies.
    active_companies = []
    for company in companies:
        # TODO: Replace with the actual field or logic to determine active status.
        if company.get("status", "").lower() == "active":
            active_companies.append(company)

    # Enrich active companies with LEI data.
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

    # Update the job record in the external entity_service.
    update_data = {"status": "completed", "results": results}
    # The meta field is used here to indicate which job to update.
    entity_service.update_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=update_data,
        meta={"technical_id": job_id}
    )

# POST endpoint: process external calls and store resulting enriched company data.
@app.route("/companies/search", methods=["POST"])
@validate_request(CompanySearchRequest)  # For POST requests, place after @app.route (workaround for quart-schema issue)
@validate_response(CompanySearchResponse, 200)
async def search_companies(data: CompanySearchRequest):
    """Initiate company search and enrichment."""
    company_name = data.companyName
    if not company_name:
        abort(400, description="Missing required field: companyName")

    # Create a unique job id and note the requested time.
    requested_at = datetime.datetime.utcnow().isoformat() + "Z"
    job_data = {
        "status": "processing",
        "requestedAt": requested_at,
        "results": []
    }
    # Persist the job using the external repository.
    job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_data  # the validated data object for persistence
    )

    # Fire and forget the processing task.
    # TODO: In production, add better task handling and error logging.
    asyncio.create_task(process_entity(job_id, data.__dict__))

    # Immediate response with searchId; results may be pending.
    return CompanySearchResponse(searchId=job_id, results=[])

# GET endpoint: Retrieve processed search results using a path parameter.
# Note: No validation is applied here because we are not expecting a query string.
@app.route("/companies/results/<job_id>", methods=["GET"])
async def get_results(job_id):
    """Retrieve stored enriched results by searchId."""
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        abort(404, description="Job ID not found.")

    # Compose a response that includes the searchId (job id) along with the job data.
    response = {
        "searchId": job_id,
        "results": job.get("results"),
        "status": job.get("status"),
        "requestedAt": job.get("requestedAt")
    }
    return jsonify(response)

# A simple test endpoint for checking service health.
@app.route("/", methods=["GET"])
async def index():
    return "Finnish Companies Data Retrieval and Enrichment Prototype is running."

if __name__ == '__main__':
    # Entry point as specified.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
────────────────────────────────────────────────────────────────────────────

Notes:
1. In the POST endpoint, a new job item is added via entity_service.add_item. The returned id is then passed back to the client so that it can later query job results.
2. In process_entity the job record is updated via entity_service.update_item with meta={"technical_id": job_id} to indicate which job should be updated.
3. The GET endpoint now simply retrieves the job data from the external repository using entity_service.get_item.
4. All original business logic (calling external APIs, filtering/enriching data, etc.) is preserved.
5. If additional functionality is needed from the external API (or if a function such as get_items_by_condition is necessary) further refactoring would be needed.

This solution meets the requirement to remove the local cache and replace it with calls to the external entity_service while preserving the core business logic.