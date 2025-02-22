#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import aiohttp
import datetime
import uuid

from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring

# Import and initialize external cyoda dependencies.
# ENTITY_VERSION should be defined as a constant in your configuration.
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)  # Enable Quart Schema integration

# Startup hook for external cyoda initialization.
@app.before_serving
async def startup():
    try:
        await init_cyoda(cyoda_token)
    except Exception as ex:
        # Log or handle initialization errors appropriately.
        app.logger.error(f"Error initializing cyoda: {ex}")
        raise ex

# -----------------------------------------------------------------------------
# Dataclass definitions for input validation and output responses.
# -----------------------------------------------------------------------------
@dataclass
class SearchRequest:
    companyName: str
    # Additional filters can be added later, for instance:
    # registrationDateStart: Optional[str] = None
    # registrationDateEnd: Optional[str] = None

@dataclass
class SearchResponse:
    jobId: str
    status: str
    message: str

@dataclass
class ResultsQuery:
    jobId: str

@dataclass
class ResultsResponse:
    jobId: str
    status: str
    requestedAt: str
    results: list = None
    error: str = None

# -----------------------------------------------------------------------------
# POST endpoint: /api/companies/search
#
# This endpoint initiates a company search. It creates a new job record with the
# minimal required data (including the companyName) and provides the workflow function
# in the call to entity_service.add_item. The workflow function (process_companies)
# will run asynchronously before the record is persisted.
# -----------------------------------------------------------------------------
@app.route("/api/companies/search", methods=["POST"])
@validate_request(SearchRequest)
@validate_response(SearchResponse, 202)
async def search_company(data: SearchRequest):
    """
    Initiates a search for companies by name.

    The endpoint performs minimal processing:
        - Validates request input.
        - Constructs the job record.
        - Adds a new entity record through entity_service.add_item while specifying the workflow function.

    The heavy lifting (fetching data from the external API, filtering active companies,
    enrichment with LEI data) is performed inside the workflow function process_companies.

    Potential issues preventions:
        - Missing companyName in the request is checked early.
        - Any processing errors are handled inside process_companies.
    """
    # Ensure that companyName is provided.
    if not data.companyName:
        return jsonify({"error": "companyName is required"}), 400

    # Timestamp for when the request is made.
    requested_at = datetime.datetime.utcnow().isoformat() + "Z"
    # Build the initial job data. Notice that we include the companyName,
    # which the workflow function will use.
    job_data = {
        "status": "processing",
        "requestedAt": requested_at,
        "companyName": data.companyName
    }

    # Create the new job record by passing the workflow function.
    # The workflow function (process_companies) will be executed asynchronously
    # prior to persistence, updating the entity's internal state.
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,  # Always use this constant.
        entity=job_data,                # Job record including the companyName.
        workflow=process_companies      # Workflow function that processes the entity.
    )

    # Return a response containing the Job ID (so that the client may poll results later).
    return SearchResponse(jobId=job_id, status="processing", message="Search initiated"), 202

# -----------------------------------------------------------------------------
# GET endpoint: /api/companies/results
#
# This endpoint retrieves the job record based on the jobId query parameter.
# -----------------------------------------------------------------------------
@validate_querystring(ResultsQuery)  # Ensure proper query string validation.
@app.route("/api/companies/results", methods=["GET"])
async def get_results():
    """
    Retrieves the processed search results for a given jobId provided as query parameter.

    The endpoint performs validation and then calls out to the entity_service.get_item
    to fetch the job record. Error responses are returned in case the jobId is missing or not found.
    """
    job_id = request.args.get("jobId")
    if not job_id:
        return jsonify({"error": "jobId is required"}), 400

    # Retrieve the job record using entity_service.
    job_data = await entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job_data:
        return jsonify({"error": "Job not found"}), 404

    response = ResultsResponse(
        jobId=job_id,
        status=job_data.get("status"),
        requestedAt=job_data.get("requestedAt", ""),
        results=job_data.get("results"),
        error=job_data.get("error")
    )
    return jsonify(response)

# -----------------------------------------------------------------------------
# Main application runner.
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    # Running the Quart app with debugging turned on and specifying host and port.
    # Note: use_reloader is disabled to avoid multiple initializations.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
