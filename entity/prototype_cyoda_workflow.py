#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring
import aiohttp

from common.config.config import ENTITY_VERSION
from app_init.app_init import cyoda_token, entity_service
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@dataclass
class EnrichRequest:
    companyName: str
    registrationDateStart: str = None
    registrationDateEnd: str = None

@dataclass
class EnrichResponse:
    job_id: str
    message: str
    requestedAt: str

@dataclass
class ResultsQuery:
    job_id: str

# Helper function to simulate external LEI lookup
async def fetch_lei_for_company(company):
    # TODO: Replace with an actual call to a reliable LEI API if available.
    await asyncio.sleep(0.1)  # Simulate network delay
    if "Example" in company.get("companyName", ""):
        return "EXAMPLE-LEI-001"
    return "Not Available"

# Workflow function applied to the companies_job entity before it is persisted.
# This function can perform asynchronous tasks (fire and forget) and modify the entity state.
async def process_companies_job(entity: dict):
    # Mark that the workflow function has been applied
    entity["workflow_applied_at"] = datetime.datetime.utcnow().isoformat()
    entity["workflow_processed"] = True
    # Launch asynchronous enrichment processing using the request data stored in the entity.
    # Note: We are not updating the current entity via entity_service here; instead we schedule
    # an asynchronous task that can update the entity later.
    asyncio.create_task(
        process_entity(
            job_id=entity["technical_id"],
            request_data={
                "companyName": entity.get("companyName"),
                "registrationDateStart": entity.get("registrationDateStart"),
                "registrationDateEnd": entity.get("registrationDateEnd")
            }
        )
    )

# Process job asynchronously; this function updates the job record (in a fire-and-forget manner)
async def process_entity(job_id, request_data: dict):
    results = []
    company_name = request_data.get("companyName")
    registration_date_start = request_data.get("registrationDateStart")
    registration_date_end = request_data.get("registrationDateEnd")
    
    params = {"name": company_name}
    # TODO: Include other query parameters if needed.

    try:
        async with aiohttp.ClientSession() as session:
            external_api_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
            async with session.get(external_api_url, params=params) as resp:
                if resp.status != 200:
                    job = entity_service.get_item(
                        token=cyoda_token,
                        entity_model="companies_job",
                        entity_version=ENTITY_VERSION,
                        technical_id=job_id
                    )
                    job["status"] = "error"
                    job["results"] = {"error": f"External API returned status {resp.status}"}
                    entity_service.update_item(
                        token=cyoda_token,
                        entity_model="companies_job",
                        entity_version=ENTITY_VERSION,
                        entity=job,
                        meta={}
                    )
                    return
                companies_data = await resp.json()
                companies = companies_data.get("results", [])
    except Exception as e:
        job = entity_service.get_item(
            token=cyoda_token,
            entity_model="companies_job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
        job["status"] = "error"
        job["results"] = {"error": str(e)}
        entity_service.update_item(
            token=cyoda_token,
            entity_model="companies_job",
            entity_version=ENTITY_VERSION,
            entity=job,
            meta={}
        )
        return

    # TODO: Adjust filtering logic based on actual PRH API schema.
    for comp in companies:
        if comp.get("status", "").lower() != "active":
            continue
        lei_code = await fetch_lei_for_company(comp)
        enriched_company = {
            "companyName": comp.get("companyName", "Unknown"),
            "businessId": comp.get("businessId", "Unknown"),
            "companyType": comp.get("companyType", "Unknown"),
            "registrationDate": comp.get("registrationDate", "Unknown"),
            "status": "Active",
            "LEI": lei_code
        }
        results.append(enriched_company)

    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies_job",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    job["status"] = "completed"
    job["results"] = results
    entity_service.update_item(
        token=cyoda_token,
        entity_model="companies_job",
        entity_version=ENTITY_VERSION,
        entity=job,
        meta={}
    )

# POST endpoint for companies enrichment.
# Note: The endpoint is now free from any fire-and-forget logic.
@app.route("/companies/enrich", methods=["POST"])
@validate_request(EnrichRequest)  # Validate request after the route decorator.
@validate_response(EnrichResponse, 200)
async def enrich_companies(data: EnrichRequest):
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()
    # Include enrichment parameters in the job data so that they are available in the workflow function.
    job_data = {
        "technical_id": job_id,
        "status": "processing",
        "requestedAt": requested_at,
        "results": None,
        "companyName": data.companyName,
        "registrationDateStart": data.registrationDateStart,
        "registrationDateEnd": data.registrationDateEnd
    }
    # The workflow function "process_companies_job" will be invoked before persisting the entity.
    new_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies_job",
        entity_version=ENTITY_VERSION,
        entity=job_data,
        workflow=process_companies_job  # Workflow function applied before persistence.
    )
    return EnrichResponse(job_id=new_id, message="Processing started", requestedAt=requested_at)

# GET endpoint to retrieve enrichment results.
@validate_querystring(ResultsQuery)  # Validate query parameters first.
@app.route("/companies/results", methods=["GET"])
async def get_results():
    job_id = request.args.get("job_id")
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies_job",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        return jsonify({"error": "job_id not found"}), 404
    return jsonify({
        "job_id": job_id,
        "status": job.get("status"),
        "results": job.get("results"),
        "requestedAt": job.get("requestedAt")
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)