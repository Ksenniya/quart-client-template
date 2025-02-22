#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prototype.py

A working prototype for the Finnish Companies Data Retrieval and Enrichment Application.
External calls use aiohttp.ClientSession. Persistence is managed via an external service (entity_service).
The add_item function has been updated to accept an extra asynchronous workflow function.
That workflow function is applied on the newly created job entity (which includes the original payload)
immediately before its persistence. All asynchronous processing (external API calls, data filtering,
and enrichment) has been moved into this workflow function.

IMPORTANT:
 - The workflow function receives the job entity (a dict) as its only argument.
 - The workflow may modify the entity state (e.g. entity['status'] = 'completed') directly.
 - The workflow must not call any entity_service.add_item/update/delete on the same entity model
   as that could lead to infinite recursion.

Any incomplete requirements are marked with TODO comments.
"""

import asyncio
import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Any

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring
import aiohttp

# Import external service, token, and configuration version.
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Enable Quart validation via schemas

# Startup hook to initialize cyoda service.
@app.before_serving
async def startup():
    try:
        await init_cyoda(cyoda_token)
    except Exception as exc:
        print(f"Error during startup initialization of cyoda: {exc}")
        raise exc

# ----- Dataclass models for request/response validation -----

@dataclass
class CompanyFilters:
    location: Optional[str] = None
    companyForm: Optional[str] = None
    page: Optional[int] = None

@dataclass
class CompanyRequest:
    companyName: str
    filters: Optional[CompanyFilters] = None

@dataclass
class CompanyJobResponse:
    jobId: str
    status: str

# --- POST endpoint to trigger processing ---
@app.route("/companies", methods=["POST"])
@validate_request(CompanyRequest)  # Validation uses the defined dataclass
@validate_response(CompanyJobResponse, 201)
async def post_companies(data: CompanyRequest):
    """
    POST endpoint to trigger data retrieval, filtering, and enrichment.
    Accepts JSON with required field 'companyName' and optional 'filters'.
    Returns a jobId for later retrieval.

    In this version the minimal job data is stored (including the original payload) and the entire
    processing is performed by process_companies_workflow. This frees the controller of any heavy logic.
    """
    # Build the payload from the incoming request.
    payload = {
        "companyName": data.companyName,
        "filters": {
            "location": data.filters.location if data.filters else None,
            "companyForm": data.filters.companyForm if data.filters else None,
            "page": data.filters.page if data.filters else None
        } if data.filters else {}
    }
    # Create the initial job entity. Include creation timestamp and the payload.
    job_data = {
        "status": "processing",
        "requestedAt": datetime.datetime.utcnow().isoformat(),
        "payload": payload
    }

    # Make the call to persist the job.
    # entity_service.add_item is expected to invoke the workflow function (here process_companies_workflow)
    # asynchronously before final persistence.
    try:
        job_id = entity_service.add_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,  # Always use this constant
            entity=job_data,
            workflow=process_companies_workflow  # All asynchronous processing happens here.
        )
    except Exception as add_exc:
        print(f"Error creating job: {add_exc}")
        return jsonify({"error": "Unable to create job."}), 500

    response_data = CompanyJobResponse(jobId=job_id, status="processing")
    return jsonify(response_data.__dict__), 201

# --- GET endpoint to retrieve job results ---
@app.route("/companies/<job_id>", methods=["GET"])
async def get_companies(job_id: str):
    """
    GET endpoint to retrieve the processing results for a given jobId.
    No additional validation is performed on the job_id as it comes directly from the URI.
    """
    try:
        job = entity_service.get_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
    except Exception as get_exc:
        print(f"Error retrieving job {job_id}: {get_exc}")
        return jsonify({"error": "Internal error retrieving job."}), 500

    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(job)

# --- Optional extra GET endpoint (e.g., retrieve LEI for one company entry) ---
@validate_querystring(CompanyRequest)
@app.route("/companies/<string:job_id>/lei", methods=["GET"])
async def get_company_lei(job_id: str):
    """
    GET endpoint to retrieve LEI information for one of the companies in a job.
    This illustrative endpoint extracts the first company's LEI from the result set.
    """
    try:
        job = entity_service.get_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
    except Exception as exc:
        print(f"Error retrieving job {job_id}: {exc}")
        return jsonify({"error": "Internal error retrieving job."}), 500

    if not job:
        return jsonify({"error": "Job not found"}), 404

    # Retrieve the first enriched company’s LEI if available.
    result = job.get("result", [])
    lei_info = "Not Available"
    if isinstance(result, list) and result:
        first_company = result[0]
        lei_info = first_company.get("LEI", "Not Available")

    return jsonify({"jobId": job_id, "LEI": lei_info})

if __name__ == '__main__':
    # Run the Quart application. For production, consider using a production-ready ASGI server.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)