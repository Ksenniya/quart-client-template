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
# Helper Functions and Business Logic
# -------------------------------
async def fetch_company_data(params: dict):
    """
    Call the Finnish Companies Registry API to fetch company information.
    Uses the "companyName" query parameter from our input.
    """
    url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
    query_params = {"name": params.get("companyName")}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=query_params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data
                else:
                    return {"results": []}
    except Exception as e:
        # In case of network or decoding errors log error return empty results.
        return {"results": []}

async def fetch_lei_for_company(company: dict):
    """
    Fetch the Legal Entity Identifier (LEI) for a given company.
    For this prototype, a mock implementation is used.
    """
    try:
        await asyncio.sleep(0.1)  # Simulate network latency.
        if len(company.get("name", "")) % 2 == 0:
            return "529900T8BM49AURSDO55"
        else:
            return "Not Available"
    except Exception:
        return "Not Available"

async def process_entity(job_id: str, request_data: dict):
    """
    Process the job: retrieve company info, filter active companies, and enrich with LEI info.
    After processing, update the job status using entity_service.
    """
    try:
        external_data = await fetch_company_data(request_data)
        companies = external_data.get("results", [])
        active_companies = [c for c in companies if str(c.get("status", "")).lower() == "active"]
        results = []
        for company in active_companies:
            company_info = {
                "companyName": company.get("name"),
                "businessId": company.get("businessId"),
                "companyType": company.get("companyForm"),
                "registrationDate": company.get("registrationDate"),
                "status": "Active"
            }
            lei = await fetch_lei_for_company(company)
            company_info["LEI"] = lei
            results.append(company_info)
        updated_job = {
            "job_id": job_id,
            "status": "completed",
            "results": results
        }
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            entity=updated_job,
            meta={}
        )
    except Exception as e:
        updated_job = {
            "job_id": job_id,
            "status": "failed",
            "error": str(e)
        }
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            entity=updated_job,
            meta={}
        )

async def process_job(entity: dict):
    """
    Workflow function applied to the job entity prior to persistence.
    This function can modify the entity to include information necessary for asynchronous processing.
    The function schedules the asynchronous processing of the job and removes extraneous data.
    """
    # Add a timestamp indicating workflow processing.
    entity["workflow_processed_at"] = datetime.datetime.utcnow().isoformat()
    # Ensure job_id is present; if not, generate one.
    if "job_id" not in entity:
        entity["job_id"] = str(uuid.uuid4())
    # Extract request_data for async processing.
    request_data = entity.pop("request_data", {})
    # Validate that request_data is not empty (basic safeguard).
    if request_data:
        # Schedule the asynchronous processing task.
        asyncio.create_task(process_entity(entity["job_id"], request_data))
    # Return the modified entity state which will then be persisted.
    return entity

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