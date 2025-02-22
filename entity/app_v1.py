#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import datetime
import uuid
from dataclasses import dataclass
from typing import Optional

from quart import Quart, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response
import aiohttp

# Import required external service and related constants.
from common.config.config import ENTITY_VERSION
from app_init.app_init import cyoda_token, entity_service
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema for automatic validations

# Startup hook to initialize our external service (cyoda)
@app.before_serving
async def startup():
    try:
        await init_cyoda(cyoda_token)
    except Exception as e:
        # If initialization fails, log and abort early
        app.logger.error(f"Failed to initialize cyoda: {str(e)}")
        raise

# ---------------------------------------------------------------------------
# Dataclass Definitions for Request/Response Validation
# These ensure that the POST payload includes the expected fields and that the
# returned JSON data satisfies the defined schema.
# ---------------------------------------------------------------------------
@dataclass
class LookupRequest:
    companyName: str        # The company name (full or partial) is required.
    location: Optional[str] = None
    businessId: Optional[str] = None
    registrationDateStart: Optional[str] = None  # Expected in yyyy-mm-dd format.
    registrationDateEnd: Optional[str] = None      # Expected in yyyy-mm-dd format.

@dataclass
class LookupResponse:
    searchId: str  # Identifier that clients can use for follow-up GET requests.

# ---------------------------------------------------------------------------
# POST Endpoint: /companies/lookup
#
# This endpoint is intentionally "thin". It creates a job entity containing the
# essential metadata as well as the minimal request payload needed for processing.
# Then it calls entity_service.add_item with the asynchronous workflow function,
# process_companies, which will apply all business logic before the entity is persisted.
# ---------------------------------------------------------------------------
@app.route('/companies/lookup', methods=['POST'])
@validate_request(LookupRequest)
@validate_response(LookupResponse, 202)
async def lookup_companies(data: LookupRequest):
    """
    Initiates a company lookup and enrichment process.

    The caller must supply at least a "companyName".
    Additional filtering criteria can be provided as well.

    The minimal job entity is created and the processing is handled asynchronously by
    the workflow function, process_companies.
    """
    # Generate a unique job id and record the request timestamp.
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()

    # Create the initial job entity. In addition to meta-data, we store the parameters
    # that the workflow function will need.
    job_data = {
        "id": job_id,
        "status": "processing",
        "requestedAt": requested_at,
        "result": None,
        # Save the incoming request data for processing.
        "companyName": data.companyName,
        "location": data.location,
        "businessId": data.businessId,
        "registrationDateStart": data.registrationDateStart,
        "registrationDateEnd": data.registrationDateEnd,
    }

    # Submit the job to the external service including the workflow function.
    # The workflow (process_companies) is applied asynchronously to the job entity before persistence.
    try:
        entity_service.add_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,  # Always use this constant
            entity=job_data,                # The job entity created above
            workflow=process_companies      # Asynchronous workflow function
        )
    except Exception as e:
        # In case storing the job fails, log the error and return an appropriate response.
        app.logger.error(f"Failed to add job entity: {str(e)}")
        abort(500, description="Internal Error: Unable to queue the job.")

    # Return the job id immediately to the client.
    return jsonify(LookupResponse(searchId=job_id)), 202

# ---------------------------------------------------------------------------
# GET Endpoint: /companies/<job_id>
#
# This endpoint retrieves the current state of the job entity using the external service.
# It returns the processing status if not yet completed, or the final enriched result.
# ---------------------------------------------------------------------------
@app.route('/companies/<job_id>', methods=['GET'])
async def get_companies(job_id):
    """
    Retrieve the status and result of a company lookup job.

    The client should supply the job identifier (searchId) returned by POST /companies/lookup.
    """
    try:
        job = entity_service.get_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
    except Exception as e:
        app.logger.error(f"Error retrieving job {job_id}: {str(e)}")
        abort(500, description="Internal Error: Unable to retrieve job.")

    if not job:
        abort(404, description="Job not found.")

    # Return different details depending on the current status.
    if job.get("status") == "processing":
        return jsonify({
            "status": "processing",
            "requestedAt": job.get("requestedAt")
        })
    elif job.get("status") == "error":
        return jsonify({
            "status": "error",
            "error": job.get("result")
        })
    else:
        return jsonify({
            "status": "completed",
            "result": job.get("result"),
            "completedAt": job.get("workflowTimestamp")
        })

# ---------------------------------------------------------------------------
# Run the Application.
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    # You may wish to disable threading when using async libraries; however,
    # we keep threaded=True as long as careful testing is performed.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)