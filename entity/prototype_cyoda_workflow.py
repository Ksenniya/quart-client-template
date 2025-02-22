Below is one complete refactored version of the file. The only functional change (aside from all the original enrichment logic) is that the call to entity_service.add_item now passes an additional workflow function (process_companies) that is applied asynchronously to the job record before it is persisted. In this simple implementation the workflow function just tags the entity with a “workflowApplied” flag and a timestamp. (You may replace or extend its logic as needed.) All other functionality for background enrichment remains unchanged.

----------------------------------------------------------------
#!/usr/bin/env python3
import asyncio
from datetime import datetime
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response
import aiohttp

# Import external services and constants.
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Initialize quart-schema for request/response validation

# -------------------------------------------------------------------------
# Startup tasks: Initialize external system(s) before serving requests.
# -------------------------------------------------------------------------
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# -------------------------------------------------------------------------
# Data models for validation.
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
# Workflow Function
# -------------------------------------------------------------------------
async def process_companies(entity: dict) -> dict:
    """
    The workflow function applied to 'companies' entities before persistence.
    You may change or extend the entity state as needed.
    In this implementation, we simply add a marker and a timestamp.
    
    Note: DO NOT call entity_service.add_item/update_item for the same entity_model
    from within this function – that would cause infinite recursion.
    """
    entity["workflowApplied"] = True
    entity["workflowTimestamp"] = datetime.utcnow().isoformat()
    return entity

# -------------------------------------------------------------------------
# External API calls (mocks and TODOs)
# -------------------------------------------------------------------------
async def fetch_company_data(session: aiohttp.ClientSession, company_name: str):
    """
    Query the Finnish Companies Registry API using the company name.
    NOTE: Adapt this logic as needed for the actual API.
    """
    params = {"name": company_name}
    async with session.get("https://avoindata.prh.fi/opendata-ytj-api/v3/companies", params=params) as resp:
        if resp.status == 200:
            data = await resp.json()
            return data.get("results", [])
        else:
            # TODO: Add more robust error handling.
            return []

async def lookup_lei(session: aiohttp.ClientSession, company: dict):
    """
    Lookup the Legal Entity Identifier (LEI) for the company.
    This is a placeholder implementation.
    """
    await asyncio.sleep(0.1)  # Simulate network latency.
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
    This function updates the persistent job record via external service calls.
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
        # Filter active companies (we assume a company is active if its status is "active")
        active_companies = [comp for comp in companies if comp.get("status", "").lower() == "active"]

        enriched_companies = []
        for comp in active_companies:
            lei_val = await lookup_lei(session, comp)
            enriched_companies.append({
                "companyName": comp.get("companyName", "Unknown"),
                "businessId": comp.get("businessId", "Unknown"),
                "companyType": comp.get("companyType", "Unknown"),
                "registrationDate": comp.get("registrationDate", "Unknown"),
                "status": "Active",
                "LEI": lei_val,
            })

    # Update the job record with "completed" status and the enrichment results.
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
# REST API Endpoints
# -------------------------------------------------------------------------
@app.route("/companies/enrich", methods=["POST"])
@validate_request(EnrichRequest)
@validate_response(EnrichResponse, 202)
async def enrich_companies(data: EnrichRequest):
    """
    Accepts a company name and initiates the enrichment process.
    A new record is created via entity_service.add_item. The returned technical id
    is provided in the response. A workflow function (process_companies) is passed
    to add_item so that the job record is pre-processed before persistence.
    """
    requested_at = datetime.utcnow().isoformat()
    # Prepare initial job data.
    job_data = {
        "status": "queued",
        "requestedAt": requested_at,
        "results": None
    }
    # Persist the job record via entity_service.add_item and retrieve the generated id.
    # The workflow function is applied to job_data asynchronously before saving.
    job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,  # Always use this constant
        entity=job_data,                # The initial job data
        workflow=process_companies      # Workflow function applied before persistence
    )
    # Fire-and-forget: Execute a background task to enrich the record.
    asyncio.create_task(process_entity(job_id, data.__dict__))
    return jsonify({
        "jobId": job_id,
        "message": "Enrichment processing started. Use the jobId to retrieve results."
    }), 202

@app.route("/companies/results/<job_id>", methods=["GET"])
async def get_results(job_id: str):
    """
    Retrieves the enriched data for a given job id.
    The job record is fetched from the external persistent store.
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
    # threaded=True allows background async tasks to run in this prototype.
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
----------------------------------------------------------------

Notes:
1. The workflow function process_companies is a lightweight pre‐persistence handler that adds additional metadata.
2. The background task (process_entity) still handles the actual enrichment and job record updates.
3. All external interactions use the provided cyoda_token and constant ENTITY_VERSION.
4. You may expand process_companies if additional transformation or validation steps are needed before saving.
