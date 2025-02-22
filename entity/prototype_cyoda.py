Below is one acceptable refactored version of the file. Note that every operation that previously read, wrote, or updated the local in‑memory “entity_jobs” dictionary now calls the appropriate function of entity_service using the allowed functions. (For the purposes of this refactoring the entity_model is set to "companies" for all calls.) Also note that the code now imports ENTITY_VERSION from common.config.config and adds the startup hook as requested.

────────────────────────── start of file ──────────────────────────
#!/usr/bin/env python3
"""
prototype.py

A working prototype for the Finnish Companies Data Retrieval and Enrichment Application.
External calls use aiohttp.ClientSession. Persistence is now managed via an external service,
entity_service, instead of local in-memory dictionaries.
Any incomplete requirements (such as the LEI lookup logic) are marked with TODO comments.
"""

import asyncio
import uuid
import datetime
from dataclasses import dataclass
from typing import Optional

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring
import aiohttp

# Import external service and constant
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Enable Quart Schemas

# Startup hook to initialize cyoda service.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# ----- Dataclass models for request/response validation -----

@dataclass
class CompanyFilters:
    location: Optional[str] = None
    companyForm: Optional[str] = None
    page: Optional[int] = None

@dataclass
class CompanyRequest:
    companyName: str
    filters: Optional[CompanyFilters] = None

@dataclass
class CompanyJobResponse:
    jobId: str
    status: str

async def process_entity(job_id: str, data: dict):
    """
    Processes the incoming data by invoking external APIs:
      - Calls the Finnish Companies Registry API.
      - Filters out inactive companies.
      - Enriches each active company with LEI lookup.
    """
    # Step 1: Retrieve company data from the Finnish Companies Registry API.
    prh_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
    params = {"name": data.get("companyName")}
    # Additional filters if provided.
    filters = data.get("filters", {})
    if filters:
        if "location" in filters and filters["location"]:
            params["location"] = filters["location"]
        if "companyForm" in filters and filters["companyForm"]:
            params["companyForm"] = filters["companyForm"]
        if "page" in filters and filters["page"]:
            params["page"] = filters["page"]

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(prh_url, params=params) as response:
                if response.status == 200:
                    companies_data = await response.json()
                else:
                    # TODO: Handle non-200 responses as needed.
                    companies_data = {}
        except Exception as e:
            # TODO: Improve error handling (e.g., logging) here.
            companies_data = {}

    # Assume companies_data contains a list of companies under key 'results'.
    companies = companies_data.get("results", [])
    
    # Step 2: Filter out inactive companies.
    # For this prototype, we assume each company entry contains a field "status"
    # where "active" (case-insensitive) indicates an active company.
    active_companies = [company for company in companies if company.get("status", "").lower() == "active"]

    # Step 3: Enrich each active company with LEI information.
    enriched_results = []
    for company in active_companies:
        lei = await get_lei_for_company(company)
        enriched_results.append({
            "companyName": company.get("name", "Unknown"),
            "businessId": company.get("businessId", "Unknown"),
            "companyType": company.get("companyType", "Unknown"),
            "registrationDate": company.get("registrationDate", "Unknown"),
            "status": company.get("status", "Unknown"),
            "LEI": lei if lei else "Not Available"
        })

    # Update the record into the external persistence using entity_service.
    update_data = {
        "status": "completed",
        "result": enriched_results
    }
    # Update the job record.
    entity_service.update_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=update_data,
        meta={}
    )

async def get_lei_for_company(company: dict) -> Optional[str]:
    """
    Placeholder for LEI lookup.
    TODO: Replace with an actual HTTP request to a reliable LEI lookup service.
          For now, this function simulates a delay and returns a dummy LEI for companies
          whose name starts with the letter 'A' (case-insensitive).
    """
    await asyncio.sleep(0.1)
    if company.get("name", "").lower().startswith("a"):
        return "DUMMY-LEI-12345"
    return None

# --- POST endpoint to trigger processing ---
@app.route("/companies", methods=["POST"])
@validate_request(CompanyRequest)  # For POST, the route is defined first, then validation.
@validate_response(CompanyJobResponse, 201)
async def post_companies(data: CompanyRequest):
    """
    POST endpoint to trigger data retrieval, filtering, and enrichment.
    Accepts JSON with required field 'companyName' and optional 'filters'.
    Returns a jobId for retrieving results later.
    """
    # Convert dataclass to dictionary.
    data_dict = {
        "companyName": data.companyName,
        "filters": {
            "location": data.filters.location if data.filters else None,
            "companyForm": data.filters.companyForm if data.filters else None,
            "page": data.filters.page if data.filters else None
        } if data.filters else {}
    }
    requested_at = datetime.datetime.utcnow().isoformat()
    # Create initial job data.
    job_data = {
        "status": "processing",
        "requestedAt": requested_at
    }
    # Add item using the external entity_service.
    job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_data  # the validated data object
    )
    
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, data_dict))
    
    response = CompanyJobResponse(jobId=job_id, status="processing")
    return jsonify(response.__dict__), 201

# --- GET endpoint to retrieve job results ---
@app.route("/companies/<job_id>", methods=["GET"])
async def get_companies(job_id):
    """
    GET endpoint to retrieve processing results using a jobId.
    No validation of the job_id as it is taken from the path variable.
    """
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(job)

# Optional extra GET endpoint that may require query parameter validation.
# Example: Retrieving LEI for a specific company ID.
# No body is allowed for GET methods.
@validate_querystring(CompanyRequest)  # Workaround: For GET, validation (if needed) goes first.
@app.route("/companies/<string:job_id>/lei", methods=["GET"])
async def get_company_lei(job_id):
    """
    GET endpoint to retrieve LEI information for a company within a job.
    NOTE: This endpoint is illustrative. In a robust solution, you might provide more advanced query options.
    """
    # Access query parameter traditionally.
    dummy_param = request.args.get('dummy')  # TODO: Replace with actual parameter if needed.
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        return jsonify({"error": "Job not found"}), 404
    # For demonstration, just return the LEI of the first company.
    result = job.get("result", [])
    lei_info = result[0].get("LEI") if result else "Not Available"
    return jsonify({"jobId": job_id, "LEI": lei_info})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
────────────────────────── end of file ──────────────────────────

Explanation of key refactoring changes:

1. Removed the in‑memory dictionary "entity_jobs". Instead, on POST the job is stored via entity_service.add_item, and later updated via entity_service.update_item.
2. The GET endpoints now use entity_service.get_item to retrieve job details.
3. Imported ENTITY_VERSION from common.config.config and cyoda_token and entity_service from app_init.app_init.
4. Added the startup() function that initializes cyoda before the application starts serving.

This version preserves the original business logic (data ingestion, external API calls, filtering, enrichment, etc.) yet now uses the external service for persistence.