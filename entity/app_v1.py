#!/usr/bin/env python3
import asyncio
import uuid
import datetime
import logging
import aiohttp
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring

from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Startup initialization
@app.before_serving
async def startup():
    try:
        await init_cyoda(cyoda_token)
        logger.info("CYODA initialization completed.")
    except Exception as e:
        logger.exception("Failed to initialize CYODA: %s", e)

# Data classes for request/response validation
@dataclass
class CompanyRequest:
    companyName: str

@dataclass
class JobResponse:
    searchId: str
    status: str
    requestedAt: str

@dataclass
class QueryJob:
    searchId: str

################################################################################
# POST endpoint to trigger company enrichment.
# It validates the incoming JSON request, adds a job entity using the external
# service with the workflow function, and returns the unique searchId.
################################################################################
@app.route("/api/company-enrichment", methods=["POST"])
@validate_request(CompanyRequest)  # Validation occurs on the request body
@validate_response(JobResponse, 202)
async def company_enrichment(data: CompanyRequest):
    requested_at = datetime.datetime.utcnow().isoformat()
    # job_data includes the companyName to be used by the workflow function.
    job_data = {
        "status": "pending",  # initial status; will be updated in workflow
        "requestedAt": requested_at,
        "results": None,
        "companyName": data.companyName,
    }
    try:
        # Add job entity with the process_job workflow.
        job_id = entity_service.add_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            entity=job_data,
            )
    except Exception as e:
        logger.exception("Failed to add job entity: %s", e)
        return jsonify({"error": "Internal server error"}), 500
    return JobResponse(searchId=job_id, status="processing", requestedAt=requested_at), 202

################################################################################
# GET endpoint to retrieve enrichment results based on the searchId query parameter.
################################################################################
@validate_querystring(QueryJob)  # Validation occurs on query parameters
@app.route("/api/results", methods=["GET"])
async def results():
    search_id = request.args.get("searchId")
    if not search_id:
        return jsonify({"error": "Missing searchId query parameter"}), 400
    try:
        job = entity_service.get_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            technical_id=search_id
        )
    except Exception as e:
        logger.exception("Failed to retrieve job entity: %s", e)
        return jsonify({"error": "Internal server error"}), 500
    if not job:
        return jsonify({"error": "No job found with the provided searchId"}), 404
    return jsonify(job), 200

################################################################################
# Main entry point to run the Quart app.
################################################################################
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)