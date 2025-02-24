#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring
import aiohttp

from common.config.config import ENTITY_VERSION  # always use this constant
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)  # Integrate QuartSchema

# Startup initialization for external service.
@app.before_serving
async def startup():
    try:
        await init_cyoda(cyoda_token)
    except Exception as e:
        # Log or handle startup issues as necessary.
        print("Startup initialization failed:", e)

# Data classes for request and response validation
@dataclass
class SearchRequest:
    company_name: str
    registration_date_start: str = None
    registration_date_end: str = None
    businessId: str = None
    companyForm: str = None
    # Additional filters may be added as needed.

@dataclass
class SearchResponse:
    search_id: str
    status: str

# Endpoint to initiate company search.
# This endpoint only creates a job entity. The workflow function processes the job data.
@app.route("/companies/search", methods=["POST"])
@validate_request(SearchRequest)  # Validation decorator placed after route for POST (quart-schema workaround)
@validate_response(SearchResponse, 200)
async def search_companies(data: SearchRequest):
    try:
        if not data.company_name:
            return jsonify({"error": "company_name is required"}), 400

        job_id = str(uuid.uuid4())
        requested_at = datetime.datetime.utcnow().isoformat()
        # Prepare search parameters; filter out None values.
        search_params = {
            "name": data.company_name,
            "registrationDateStart": data.registration_date_start,
            "registrationDateEnd": data.registration_date_end,
            "businessId": data.businessId,
            "companyForm": data.companyForm
        }
        job_data = {
            "technical_id": job_id,
            "status": "processing",
            "requestedAt": requested_at,
            "results": None,
            "search_params": {k: v for k, v in search_params.items() if v is not None}
        }

        # Persist job using the external service.
        # The workflow function (process_company_job) is applied asynchronously before persistence.
        job_id = entity_service.add_item(
            token=cyoda_token,
            entity_model="company_job",
            entity_version=ENTITY_VERSION,
            entity=job_data,
            workflow=process_company_job
        )

        return {"search_id": job_id, "status": "processing"}
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint to retrieve job search results.
@app.route("/companies/search/<job_id>", methods=["GET"])
async def get_search_results(job_id: str):
    try:
        job = entity_service.get_item(
            token=cyoda_token,
            entity_model="company_job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
        if not job:
            return jsonify({"error": "Job ID not found"}), 404
        # Return current status if job not yet completed.
        if job.get("status") != "completed":
            return jsonify({"search_id": job_id, "status": job.get("status")})
        return jsonify({
            "search_id": job_id,
            "status": job.get("status"),
            "results": job.get("results")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)