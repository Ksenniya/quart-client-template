#!/usr/bin/env python3
"""
prototype.py

A working prototype of the Finnish Companies Data Retrieval and Enrichment Application.
Uses Quart and QuartSchema for API endpoints and aiohttp for external HTTP requests.
Persistence is handled via an external service called entity_service.
"""

import asyncio
import uuid
import datetime
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring
import aiohttp

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Startup initialization for cyoda repository
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# -------------------------------
# Data Models for Validation
# -------------------------------
@dataclass
class EnrichRequest:
    companyName: str
    location: str = None
    registrationDateStart: str = None
    registrationDateEnd: str = None

@dataclass
class EnrichResponse:
    job_id: str

@dataclass
class JobQuery:
    job_id: str

# -------------------------------
# API Endpoints
# -------------------------------
@app.route('/api/companies/enrich', methods=['POST'])
@validate_request(EnrichRequest)
@validate_response(EnrichResponse, 201)
async def enrich_companies(data: EnrichRequest):
    # Validate that required field is provided.
    if not data.companyName:
        return jsonify({"error": "Missing required field: companyName"}), 400
    # Prepare the job entity with minimal initial state.
    job = {
        "status": "processing",
        "requestedAt": datetime.datetime.utcnow().isoformat(),
        # Preserve original request data for later asynchronous processing.
        "request_data": data.__dict__
    }
    # Persist the job entity via entity_service.add_item with workflow applied before persistence.
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="job",
        entity_version=ENTITY_VERSION,
        entity=job,
        workflow=process_job  # This asynchronous workflow function can modify the job entity.
    )
    return jsonify({"job_id": job_id}), 201

@validate_querystring(JobQuery)
@app.route('/api/companies/results', methods=['GET'])
async def get_results():
    job_id = request.args.get("job_id")
    if not job_id:
        return jsonify({"error": "Missing job_id"}), 400
    job = await entity_service.get_item(
        token=cyoda_token,
        entity_model="job",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

# -------------------------------
# Entry Point
# -------------------------------
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)