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

# Asynchronous workflow function for the "company_job" entity.
# This function is invoked right before persisting the entity.
# It performs external calls and updates the entity state.
async def process_company_job(entity):
    # Mark the time when workflow processing starts.
    entity["workflow_processed_at"] = datetime.datetime.utcnow().isoformat()
    try:
        # Retrieve search parameters stored in the entity.
        search_params = entity.get("search_params", {})
        # Validate that required search parameters exist.
        if "name" not in search_params or not search_params["name"]:
            entity["status"] = "failed"
            entity["results"] = {"error": "Missing required parameter: company name"}
            return entity

        PRH_API_BASE_URL = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
        async with aiohttp.ClientSession() as session:
            # Remove any None values which might break the API call.
            params = {k: v for k, v in search_params.items() if v is not None}
            async with session.get(PRH_API_BASE_URL, params=params) as response:
                if response.status != 200:
                    entity["status"] = "failed"
                    entity["results"] = {"error": f"PRH API call failed with status {response.status}"}
                    return entity
                prh_data = await response.json()
                companies = prh_data.get("results", [])
                results = []
                for company in companies:
                    # Process only companies with active status.
                    if company.get("status", "").lower() != "active":
                        continue
                    enriched_company = {}
                    enriched_company["company_name"] = company.get("name", "N/A")
                    enriched_company["business_id"] = company.get("businessId", "N/A")
                    enriched_company["company_type"] = company.get("companyForm", "N/A")
                    enriched_company["registration_date"] = company.get("registrationDate", "N/A")
                    enriched_company["status"] = company.get("status", "N/A")
                    lei = await fetch_lei(session, enriched_company)
                    enriched_company["lei"] = lei if lei else "Not Available"
                    results.append(enriched_company)
                entity["status"] = "completed"
                entity["results"] = results
    except Exception as e:
        # Catch any unexpected errors and mark the entity as failed.
        entity["status"] = "failed"
        entity["results"] = {"error": str(e)}
    return entity  # The new state returned will be persisted.

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

# Helper function to fetch LEI for a company.
async def fetch_lei(session: aiohttp.ClientSession, company: dict) -> str:
    try:
        business_id = company.get("business_id", "")
        if business_id and business_id[-1] in "02468":
            # Placeholder logic; replace with actual async LEI call when available.
            return "529900T8BM49AURSDO55"
        else:
            return None
    except Exception as e:
        # Log error if needed and return none to avoid halting workflow.
        return None

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)