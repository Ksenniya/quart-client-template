#!/usr/bin/env python3
"""
prototype.py

A working prototype of the Finnish Companies Data Retrieval and Enrichment Application.
Uses Quart and QuartSchema for API endpoints and aiohttp for external HTTP requests.
Persistence is mocked with an in-memory dictionary.
"""

import asyncio
import uuid
import datetime
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring  # Import validators
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

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
# Local In-Memory Persistence (Mock)
# -------------------------------
jobs = {}  # jobs[job_id] = {"status": "processing", "requestedAt": <timestamp>, "results": ...}

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
    # TODO: Add more parameters if needed.
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=query_params) as resp:
            if resp.status == 200:
                data = await resp.json()
                # TODO: Validate that the structure of 'data' meets our requirements.
                return data
            else:
                # TODO: Improve error handling for external API failures.
                return {"results": []}

async def fetch_lei_for_company(company: dict):
    """
    Fetch the Legal Entity Identifier (LEI) for a given company.
    For this prototype, we use a mock implementation.
    """
    # TODO: Replace this placeholder with an actual call to a reliable LEI registry.
    await asyncio.sleep(0.1)  # Simulate network latency.
    if len(company.get("name", "")) % 2 == 0:
        return "529900T8BM49AURSDO55"
    else:
        return "Not Available"

async def process_entity(job_id: str, data: dict):
    """
    Process the request: retrieve company info, filter active companies, enrich with LEI info.
    """
    try:
        external_data = await fetch_company_data(data)
        companies = external_data.get("results", [])
        # TODO: Update filtering logic based on actual external data fields.
        active_companies = [c for c in companies if str(c.get("status", "")).lower() == "active"]
        results = []
        for company in active_companies:
            company_info = {
                "companyName": company.get("name"),           # Assuming external API defines company name as "name"
                "businessId": company.get("businessId"),        # Assuming key is "businessId"
                "companyType": company.get("companyForm"),      # Assuming key is "companyForm"
                "registrationDate": company.get("registrationDate"),  # TODO: Confirm field name from external API.
                "status": "Active"
            }
            lei = await fetch_lei_for_company(company)
            company_info["LEI"] = lei
            results.append(company_info)
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["results"] = results
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)

# -------------------------------
# API Endpoints
# -------------------------------
# POST endpoint: Note - route decorator is placed first (workaround due to Quart Schema issue)
@app.route('/api/companies/enrich', methods=['POST'])
@validate_request(EnrichRequest)  # For POST endpoints, validation comes after route definition.
@validate_response(EnrichResponse, 201)
async def enrich_companies(data: EnrichRequest):
    if not data.companyName:
        return jsonify({"error": "Missing required field: companyName"}), 400
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.datetime.utcnow().isoformat()
    }
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, data.__dict__))
    return jsonify({"job_id": job_id}), 201

# GET endpoint: For GET requests, validation must come before the route decorator (workaround note)
@validate_querystring(JobQuery)  # Workaround: Validation decorator is placed first for GET endpoints.
@app.route('/api/companies/results', methods=['GET'])
async def get_results():
    job_id = request.args.get("job_id")
    if not job_id or job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(jobs[job_id])

# -------------------------------
# Entry Point
# -------------------------------
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)