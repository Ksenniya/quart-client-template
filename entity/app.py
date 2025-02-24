#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from dataclasses import dataclass
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request, validate_response  # Workaround: For POST, decorators placed in order route then validate_request then validate_response
import aiohttp

from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

# External API URLs
PRH_API_URL = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"  # Finnish Companies Registry API
LEI_API_URL = "https://lei.example.com/api/get"  # Placeholder for LEI lookup API

# Data classes for request/response validation
@dataclass
class CompanySearchRequest:
    companyName: str
    filters: dict = None  # Additional filtering options

@dataclass
class SearchResponse:
    requestId: str
    status: str
    message: str

@app.route("/companies/search", methods=["POST"])
@validate_request(CompanySearchRequest)  # Validate incoming request against CompanySearchRequest schema.
@validate_response(SearchResponse, 201)    # Validate outgoing response schema.
async def search_companies(data: CompanySearchRequest):
    """
    POST endpoint to trigger company search.
    It creates a job entity that stores parameters and delegates complex task processing
    to the workflow function (process_companies_search_job) invoked right before persistence.
    """
    requested_at = datetime.datetime.utcnow().isoformat()
    # Generate a unique job id
    job_id = str(uuid.uuid4())
    # Prepare job data with search parameters
    job_data = {
        "id": job_id,  # Unique job identifier for later retrieval
        "status": "processing",
        "requestedAt": requested_at,
        "searchParams": {
            "companyName": data.companyName,
            "filters": data.filters
        }
    }
    try:
        # Add job entity with workflow function that will modify the entity state asynchronously.
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="companies_search_job",
            entity_version=ENTITY_VERSION,
            entity=job_data,
            )
    except Exception as e:
        # Return error response if persisting job fails
        print(f"Error creating job: {e}")
        return jsonify({
            "requestId": job_id,
            "status": "failed",
            "message": "Unable to create a job for the search request."
        }), 500

    return jsonify({
        "requestId": job_id,
        "status": "processing",
        "message": "Your request is being processed. Retrieve results using GET /companies/result/<requestId>"
    }), 201

@app.route("/companies/result/<string:request_id>", methods=["GET"])
async def get_company_results(request_id: str):
    """
    GET endpoint to retrieve the search job results based on the provided job id.
    It returns status information and, if available, the enriched company results.
    """
    try:
        job = await entity_service.get_item(
            token=cyoda_token,
            entity_model="companies_search_job",
            entity_version=ENTITY_VERSION,
            technical_id=request_id
        )
    except Exception as e:
        print(f"Error retrieving job {request_id}: {e}")
        return jsonify({"error": "Unable to retrieve request status."}), 500

    if not job:
        return jsonify({"error": "Request ID not found"}), 404

    if job.get("status") != "completed":
        return jsonify({
            "requestId": request_id,
            "status": job.get("status"),
            "message": "Results are not yet ready. Please try again later."
        }), 202

    return jsonify({
        "requestId": request_id,
        "results": job.get("results", [])
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)