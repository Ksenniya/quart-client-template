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

# POST endpoint for companies enrichment.
# The heavy asynchronous processing is moved into the workflow function.
@app.route("/companies/enrich", methods=["POST"])
@validate_request(EnrichRequest)  # Validate request after the route decorator.
@validate_response(EnrichResponse, 200)
async def enrich_companies(data: EnrichRequest):
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()
    # Create job entity with all required parameters.
    job_data = {
        "technical_id": job_id,
        "status": "processing",
        "requestedAt": requested_at,
        "results": None,
        # Include request parameters to be used later by the workflow function.
        "companyName": data.companyName,
        "registrationDateStart": data.registrationDateStart,
        "registrationDateEnd": data.registrationDateEnd
    }
    # The workflow function "process_companies_job" will be invoked asynchronously
    # before persisting the entity, allowing any additional tasks to be fired.
    new_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies_job",
        entity_version=ENTITY_VERSION,
        entity=job_data,
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