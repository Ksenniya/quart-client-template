#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from quart import Quart, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response  # For POST, route decorator must come first, then validate_request then validate_response.
import aiohttp

from common.config.config import ENTITY_VERSION
from app_init.app_init import cyoda_token, entity_service
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Enable QuartSchema

# Data classes for request and response payloads
@dataclass
class FinnishCompanyQuery:
    companyName: str
    location: Optional[str] = None
    registrationDateStart: Optional[str] = None
    registrationDateEnd: Optional[str] = None

@dataclass
class QueryResponse:
    queryId: str
    status: str
    requestedAt: str

# Startup: initialize cyoda integration
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# POST endpoint: create company query.
@app.route('/api/finnish-companies', methods=['POST'])
@validate_request(FinnishCompanyQuery)  # Validate request payload.
@validate_response(QueryResponse, 200)     # Validate response payload.
async def create_company_query(data: FinnishCompanyQuery):
    # Generate unique job identifier and timestamp.
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat() + "Z"

    # Create initial job data and embed query parameters for processing.
    job_data = {
        "queryId": job_id,
        "status": "processing",
        "requestedAt": requested_at,
        "results": None,
        "queryParams": data.__dict__
    }

    # Add job to external entity service with the workflow function.
    # The workflow function (process_finnish_company_query) will be invoked asynchronously
    # before the entity is persisted. It contains all the processing logic.
    stored_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="finnish_company_query",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_data,
        workflow=process_finnish_company_query  # Workflow function applied to the entity.
    )
    return QueryResponse(queryId=stored_id, status="processing", requestedAt=requested_at)

# GET endpoint: get query results.
@app.route('/api/results/<job_id>', methods=['GET'])
async def get_query_results(job_id: str):
    # Retrieve the job from the external entity service.
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="finnish_company_query",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        abort(404, description="Query ID not found")
    return jsonify(job)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)