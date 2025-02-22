Below is one acceptable refactored version of prototype.py. In this version the in‑memory cache (the entity_jobs dictionary) is removed. Instead, when a new enrichment job is received the code calls entity_service.add_item to persist the job record (with an initial status of "queued") and returns the generated id in the response. In the background processing task process_entity the job record is updated via entity_service.update_item – first setting the status to "processing" and later updating it with enriched results and completed status. Finally, the GET endpoint uses entity_service.get_item to retrieve the job record by id. (All external service calls use the provided functions and the constant ENTITY_VERSION). Also, the startup function (executed before serving requests) is added per instructions.

Below is the complete updated code:

------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
from datetime import datetime
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response
import aiohttp

# Import the external entity_service as well as the token and constant for versioning.
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Startup tasks: Initialize cyoda (external system) before serving.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# -------------------------------------------------------------------------
# Data models for validation. Only primitives are used.
# -------------------------------------------------------------------------
@dataclass
class EnrichRequest:
    companyName: str
    outputFormat: str = "json"  # Optional; default is JSON.

@dataclass
class EnrichResponse:
    jobId: str
    message: str

# -------------------------------------------------------------------------
# External Calls (with mocks and TODOs)
# -------------------------------------------------------------------------
async def fetch_company_data(session: aiohttp.ClientSession, company_name: str):
    """
    Query the Finnish Companies Registry API using the company name.
    Invoked internally via the POST endpoint.
    """
    params = {"name": company_name}
    async with session.get("https://avoindata.prh.fi/opendata-ytj-api/v3/companies", params=params) as resp:
        if resp.status == 200:
            data = await resp.json()
            # TODO: Adapt to the actual structure of the API response.
            return data.get("results", [])
        else:
            # TODO: Add more robust error handling.
            return []

async def lookup_lei(session: aiohttp.ClientSession, company):
    """
    Lookup the Legal Entity Identifier (LEI) for the company.
    This is currently a placeholder.
    """
    await asyncio.sleep(0.1)  # Simulated network latency.
    # TODO: Replace with an actual call to an LEI lookup service.
    if len(company.get("companyName", "")) % 2 == 0:
        return "5493001KJTIIGC8Y1R12"
    else:
        return "Not Available"

# -------------------------------------------------------------------------
# Background Processing Task
# -------------------------------------------------------------------------
async def process_entity(job_id: str, input_data: dict):
    """
    Background task to retrieve and enrich company data.
    Instead of using a local cache, this function updates the persistent record
    via external service calls.
    """
    # Update the job status to "processing"
    processing_update = {
        "technical_id": job_id,
        "status": "processing"
    }
    entity_service.update_item(
        token=cyoda_token,
        entity_model="companies",       # Using "companies" as the entity model
        entity_version=ENTITY_VERSION,
        entity=processing_update,
        meta={}
    )

    company_name = input_data.get("companyName")
    async with aiohttp.ClientSession() as session:
        companies = await fetch_company_data(session, company_name)
        # Determine active companies (we assume a company is active if its status is "active").
        active_companies = []
        for comp in companies:
            if comp.get("status", "").lower() == "active":
                active_companies.append(comp)

        enriched_companies = []
        for comp in active_companies:
            lei_val = await lookup_lei(session, comp)
            enriched_companies.append({
                "companyName": comp.get("companyName", "Unknown"),  # Adjust field if needed.
                "businessId": comp.get("businessId", "Unknown"),
                "companyType": comp.get("companyType", "Unknown"),
                "registrationDate": comp.get("registrationDate", "Unknown"),
                "status": "Active",
                "LEI": lei_val,
            })

    # Update job record with completed status and results
    completed_update = {
        "technical_id": job_id,
        "status": "completed",
        "results": enriched_companies,
        "completedAt": datetime.utcnow().isoformat()
    }
    entity_service.update_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        entity=completed_update,
        meta={}
    )

# -------------------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------------------
# POST /companies/enrich
# Note: For POST endpoints, route decorator goes first, then validation decorators.
# This ordering is a workaround for an issue with quart-schema.
@app.route("/companies/enrich", methods=["POST"])
@validate_request(EnrichRequest)
@validate_response(EnrichResponse, 202)
async def enrich_companies(data: EnrichRequest):
    """
    Accepts a company name and initiates the enrichment process.
    Instead of using local memory, a new record is created via entity_service.add_item.
    The returned technical id is included in the response.
    """
    requested_at = datetime.utcnow().isoformat()
    # Create initial job data to store externally.
    job_data = {
        "status": "queued",
        "requestedAt": requested_at,
        "results": None
    }
    # Persist the job record via entity_service and retrieve the generated id.
    job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_data  # the validated data object (here, a dict with initial state)
    )
    # Fire and forget: process_entity is executed asynchronously.
    asyncio.create_task(process_entity(job_id, data.__dict__))
    return jsonify({
        "jobId": job_id,
        "message": "Enrichment processing started. Use the jobId to retrieve results."
    }), 202

# GET /companies/results/<job_id>
@app.route("/companies/results/<job_id>", methods=["GET"])
async def get_results(job_id: str):
    """
    Retrieves the enriched data for a given job id.
    Instead of querying an in-memory cache, the job record is fetched via entity_service.get_item.
    """
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        return jsonify({"error": "Job not found"}), 404

    if job.get("status") != "completed":
        return jsonify({
            "jobId": job_id,
            "status": job.get("status"),
            "message": "Results are not ready yet."
        }), 202

    return jsonify({
        "jobId": job_id,
        "results": job.get("results", [])
    }), 200

if __name__ == '__main__':
    # Using threaded=True to allow background async tasks to run in this prototype.
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
------------------------------------------------

Notes:
1. The entity model used here is "companies". Adjust it, if needed, based on your domain.
2. All interactions with the job data now use calls to entity_service.add_item, update_item, and get_item.
3. All other business logic (external API calls, enrichment calculations, and validations) is preserved.
4. If additional functions (e.g. get_items or get_items_by_condition) are needed in the future, they can be similarly integrated.