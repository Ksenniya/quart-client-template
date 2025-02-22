#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import datetime
import logging
import aiohttp

from dataclasses import dataclass
from quart import Quart, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response

# New imports for external entity persistence and cyoda startup.
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

# Configure basic logging.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Quart(__name__)
QuartSchema(app)

# Startup handler to initialize cyoda
@app.before_serving
async def startup():
    try:
        await init_cyoda(cyoda_token)
    except Exception as e:
        logger.exception("Error during cyoda initialization.")
        raise

# ---------------------------------------------------------------------------
# Data classes for request/response objects.
@dataclass
class CompanySearchRequest:
    companyName: str
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
    results: list  # List of dictionaries holding company data

# ---------------------------------------------------------------------------
# POST endpoint: Only minimal controller logic; all heavy lifting is done by process_companies.
@app.route("/companies/search", methods=["POST"])
@validate_request(CompanySearchRequest)
@validate_response(CompanySearchResponse, 200)
async def search_companies(data: CompanySearchRequest):
    """
    Initiates a company search.
    The controller only validates input and creates the job entity.
    The workflow function process_companies (passed as workflow) performs the external API calls, filtering,
    enrichment and updates the entity before it is persisted.
    """
    if not data.companyName:
        abort(400, description="Missing required field: companyName")

    # Create the basic job entity.
    requested_at = datetime.datetime.utcnow().isoformat() + "Z"
    job_data = {
        "companyName": data.companyName,
        "status": "processing",
        "requestedAt": requested_at,
        "results": []  # will be filled by the workflow function
    }

    # Persist the job entity using the external repository.
    # The workflow function is applied asynchronously before the entity is persisted.
    try:
        job_id = entity_service.add_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=job_data,
            workflow=process_companies  # workflow function that performs the enrichment asynchronously
        )
    except Exception as e:
        logger.exception("Failed to add item using entity_service: %s", e)
        abort(500, description="Internal server error while creating job.")

    # Return immediately with the search/job ID.
    return CompanySearchResponse(searchId=job_id, results=[])

# ---------------------------------------------------------------------------
# GET endpoint: Retrieve the job using the provided job_id.
@app.route("/companies/results/<job_id>", methods=["GET"])
async def get_results(job_id):
    """
    Retrieves stored results for a given job ID.
    Validates that a job exists and then returns the job's entity data.
    """
    try:
        job = entity_service.get_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
    except Exception as e:
        logger.exception("Error fetching job with ID %s: %s", job_id, e)
        abort(500, description="Internal server error while retrieving job.")

    if not job:
        abort(404, description="Job ID not found.")

    response = {
        "searchId": job_id,
        "results": job.get("results"),
        "status": job.get("status"),
        "requestedAt": job.get("requestedAt")
    }
    return jsonify(response)

# ---------------------------------------------------------------------------
# Basic health check endpoint.
@app.route("/", methods=["GET"])
async def index():
    return "Finnish Companies Data Retrieval and Enrichment Prototype is running."

# ---------------------------------------------------------------------------
if __name__ == '__main__':
    # Run the Quart application.
    # Note: threaded=True is provided for compatibility in some deployments.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)