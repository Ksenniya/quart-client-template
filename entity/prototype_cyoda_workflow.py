#!/usr/bin/env python3
"""
prototype.py

A working prototype of the Finnish Companies Data Retrieval and Enrichment Application.
Uses Quart and QuartSchema for API endpoints and aiohttp for external HTTP requests.
Persistence is now handled via an external service called entity_service.
"""

import asyncio
import uuid
import datetime
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring  # Import validators
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
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=query_params) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data
            else:
                return {"results": []}

async def fetch_lei_for_company(company: dict):
    """
    Fetch the Legal Entity Identifier (LEI) for a given company.
    For this prototype, we use a mock implementation.
    """
    await asyncio.sleep(0.1)  # Simulate network latency.
    if len(company.get("name", "")) % 2 == 0:
        return "529900T8BM49AURSDO55"
    else:
        return "Not Available"

async def process_entity(job_id: str, data: dict):
    """
    Process the request: retrieve company info, filter active companies, enrich with LEI info.
    After processing, update the job status using entity_service.
    """
    try:
        external_data = await fetch_company_data(data)
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

async def process_job(entity):
    # This workflow function will be applied to the job entity before it is persisted.
    # For demonstration, we add a timestamp indicating when the workflow was applied.
    entity["workflow_processed_at"] = datetime.datetime.utcnow().isoformat()
    return entity

# -------------------------------
# API Endpoints
# -------------------------------
@app.route('/api/companies/enrich', methods=['POST'])
@validate_request(EnrichRequest)
@validate_response(EnrichResponse, 201)
async def enrich_companies(data: EnrichRequest):
    if not data.companyName:
        return jsonify({"error": "Missing required field: companyName"}), 400
    job = {
        "status": "processing",
        "requestedAt": datetime.datetime.utcnow().isoformat()
    }
    # Add workflow function as parameter to entity_service.add_item
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="job",
        entity_version=ENTITY_VERSION,
        entity=job,
        workflow=process_job  # Workflow function applied to the entity before persistence.
    )
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, data.__dict__))
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