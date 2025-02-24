#!/usr/bin/env python3
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass, asdict

import aiohttp
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_response  # Workaround for POST endpoints

from common.config.config import ENTITY_VERSION  # Always use this constant
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

ENTITY_MODEL = "companies_jobs"  # Entity model name used in entity_service calls

# Startup initialization for external service
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Dataclass for POST request validation (only primitives are used)
@dataclass
class CompanyEnrichRequest:
    companyName: str
    filters: dict = None  # TODO: Consider refining filters schema if required

# Dataclass for POST response validation
@dataclass
class EnrichResponse:
    taskId: str
    message: str

# POST endpoint: Create job and process it using the workflow function.
@app.route('/companies/enrich', methods=['POST'])
@validate_request(CompanyEnrichRequest)  # For POST, validation is applied after the route decorator
@validate_response(EnrichResponse, 201)
async def enrich_companies(data: CompanyEnrichRequest):
    # Convert the validated dataclass to a dictionary.
    input_data = asdict(data)
    if not input_data.get("companyName"):
        return jsonify({"error": "companyName is required"}), 400

    requested_at = datetime.utcnow().isoformat()
    # Include input_data in the job entity so that the workflow function can access it.
    job_data = {
        "status": "processing",
        "requestedAt": requested_at,
        "input": input_data,
        "results": None
    }
    # Persist the job using the external entity_service with an attached workflow function.
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model=ENTITY_MODEL,
        entity_version=ENTITY_VERSION,  # Always use this constant
        entity=job_data,  # The job entity containing input data
        workflow=process_companies_jobs  # Workflow function applied asynchronously before persistence.
    )

    return EnrichResponse(taskId=job_id, message="Data retrieval and enrichment in progress or completed."), 201

# GET endpoint: Retrieve enriched results.
@app.route('/companies/results/<job_id>', methods=['GET'])
async def get_results(job_id):
    job = await entity_service.get_item(
        token=cyoda_token,
        entity_model=ENTITY_MODEL,
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        return jsonify({"error": "Task ID not found"}), 404

    return jsonify({
        "taskId": job_id,
        "status": job.get("status"),
        "requestedAt": job.get("requestedAt"),
        "completedAt": job.get("completedAt"),
        "results": job.get("results"),
        "error": job.get("error", None)
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)