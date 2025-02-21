Below is one example of a refactored file. In this version the previous in‑memory cache (the entity_jobs dictionary) has been removed and all job storage and retrieval is done via calls to the external service (entity_service). In addition, the new startup code has been added. (Note: In this example the entity_model is set to "companies_job" – adjust as needed.) 

--------------------------------------------------
#!/usr/bin/env python3
"""
Prototype implementation for the Finnish Companies Data Retrieval and Enrichment Application.
Note: This is a working prototype. Proper error handling, security, persistence, and production‐grade
design should be added when moving toward a complete implementation.
"""

import asyncio
import uuid
import datetime
import random
from dataclasses import dataclass
from typing import Optional

from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response  # validate_querystring if needed
import aiohttp

# Import constants and external service entry points.
from common.config.config import ENTITY_VERSION
from app_init.app_init import cyoda_token, entity_service
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Add startup code to initialize external systems.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Dataclass for POST request validation.
@dataclass
class CompanySearchRequest:
    companyName: str
    # TODO: Add other fields (location, businessId, etc.) as needed, using primitives only.

# Dataclass for POST response validation.
@dataclass
class CompanySearchResponse:
    jobId: str
    status: str

# POST endpoint: Validation decorators for POST should appear after the @app.route decorator.
@app.route("/companies/search", methods=["POST"])
@validate_request(CompanySearchRequest)  # Workaround for Quart Schema ordering issue: this decorator comes after @app.route for POST.
@validate_response(CompanySearchResponse, 202)
async def search_companies(data: CompanySearchRequest):
    """
    Accepts a search request, fires off background processing for retrieving and enriching
    company data, and returns a job_id so the client can poll for results.
    """
    # 'data' is already validated as a CompanySearchRequest instance.
    # Convert dataclass to dict for internal usage.
    search_data = {"companyName": data.companyName}
    # TODO: Populate additional parameters if provided in CompanySearchRequest.

    # Create a job record with a unique ID.
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()
    job_data = {"status": "processing", "requestedAt": requested_at, "results": None}

    # Store initial job details via the external entity service.
    job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies_job",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_data
    )

    # Fire and forget background processing task.
    asyncio.create_task(process_entity(job_id, search_data))
    return jsonify({"jobId": job_id, "status": "processing"}), 202

# GET endpoint using URL parameter: no request body so no validation is applied.
@app.route("/companies/result/<job_id>", methods=["GET"])
async def get_results(job_id: str):
    """
    Returns the processed, enriched results based on job_id.
    """
    # Retrieve job details from the external entity service.
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies_job",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        abort(404, description="Job not found")
    return jsonify({
        "jobId": job_id,
        "status": job.get("status"),
        "results": job.get("results")
    })

async def process_entity(job_id: str, search_data: dict):
    """
    Processes the search: calls the Finnish Companies Registry API,
    filters result data, enriches with LEI data, and stores final results.
    """
    try:
        async with aiohttp.ClientSession() as session:
            # --- Step 1: Query the Finnish Companies Registry API ---
            # Build query parameters. Here we use companyName from the input.
            params = {"name": search_data.get("companyName")}
            # TODO: Incorporate additional parameters (location, businessId, etc.) as needed.
            async with session.get("https://avoindata.prh.fi/opendata-ytj-api/v3/companies", params=params) as response:
                if response.status != 200:
                    # When response fails, update the external job record accordingly.
                    update_job = {
                        "status": "failed",
                        "results": {"error": "Failed to retrieve company data"}
                    }
                    entity_service.update_item(
                        token=cyoda_token,
                        entity_model="companies_job",
                        entity_version=ENTITY_VERSION,  # always use this constant
                        entity=update_job,
                        meta={"technical_id": job_id}
                    )
                    return
                prh_data = await response.json()
                # TODO: Adapt parsing logic according to the actual API response structure.
                companies = prh_data.get("results", [])

            # --- Step 2: Filter Inactive Companies ---
            # Assumes each record contains a "status" field.
            active_companies = [company for company in companies if company.get("status", "").lower() == "active"]
            # TODO: Implement further filtering for companies with multiple names if required.

            # --- Step 3: Data Enrichment: External LEI lookup ---
            enriched_companies = []
            for company in active_companies:
                # Build a simplified company result.
                enriched_company = {
                    "companyName": company.get("name", "N/A"),
                    "businessId": company.get("businessId", "N/A"),
                    "companyType": company.get("companyType", "N/A"),
                    "registrationDate": company.get("registrationDate", "N/A"),
                    "status": "Active",  # Only active companies are processed.
                    "LEI": "Not Available"  # Default value.
                }
                # TODO: Map additional fields from API response as needed.
                lei = await lookup_lei(session, enriched_company)
                enriched_company["LEI"] = lei
                enriched_companies.append(enriched_company)

            # --- Step 4: Store final results via the external service ---
            update_job = {
                "status": "completed",
                "results": enriched_companies
            }
            entity_service.update_item(
                token=cyoda_token,
                entity_model="companies_job",
                entity_version=ENTITY_VERSION,  # always use this constant
                entity=update_job,
                meta={"technical_id": job_id}
            )

    except Exception as e:
        # On exception update the job with a failure status and error details.
        update_job = {
            "status": "failed",
            "results": {"error": str(e)}
        }
        entity_service.update_item(
            token=cyoda_token,
            entity_model="companies_job",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=update_job,
            meta={"technical_id": job_id}
        )

async def lookup_lei(session: aiohttp.ClientSession, company: dict) -> str:
    """
    Simulates the lookup of the Legal Entity Identifier (LEI) from an external service.
    Returns a dummy LEI or "Not Available".
    """
    # TODO: Replace simulation with an actual HTTP call using session when LEI API details are available.
    await asyncio.sleep(0.5)  # Simulate network delay.
    if random.choice([True, False]):
        # Generate a dummy LEI (20 characters, alphanumeric).
        return "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=20))
    else:
        return "Not Available"

if __name__ == '__main__':
    # Note: This app.run configuration is for development/testing. In production use a production ASGI server.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
--------------------------------------------------

Comments:
• All interactions with the previously in‑memory job cache now use entity_service.add_item to create,
  entity_service.update_item to update, and entity_service.get_item to retrieve job data.
• The POST /companies/search endpoint returns the job id from the external service so clients can later poll
  using GET /companies/result/<job_id>.
• Existing business logic (data ingestion, external API calls, enrichment, etc.) is preserved.
• Adjust the entity_model string ("companies_job") according to your entity naming conventions.
• If additional functions (get_items, get_items_by_condition, delete_item) are needed in the future, they can be incorporated
  in a similar fashion using the provided service functions.
  
This refactored code meets the requirements while keeping essential business logic unchanged.