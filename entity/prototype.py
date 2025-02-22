#!/usr/bin/env python3
import asyncio
import uuid
import datetime
import json
from dataclasses import dataclass
from typing import Optional

from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response  # Workaround: For POST, route decorator comes first, then validators.
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Data validation models
@dataclass
class SearchRequest:
    companyName: str
    # TODO: Add a 'filters' field once requirements are clarified (e.g., Optional[dict]) using primitive types if possible.

@dataclass
class SearchResponse:
    searchId: str
    status: str
    requestedAt: str

# In-memory cache to simulate persistence
entity_jobs = {}  # job_id -> {"status": "processing/success/failure", "requestedAt": ..., "results": ...}

# Constants for external API endpoints
FINNISH_API_URL = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
# TODO: Define the actual LEI lookup URL or mechanism below
LEI_API_URL = "https://example.com/lei-lookup"  # Placeholder URL

async def fetch_companies(session, company_name, filters):
    # Construct query parameters: currently using only companyName
    params = {"name": company_name}
    # TODO: Add additional parameters based on filters if available.
    async with session.get(FINNISH_API_URL, params=params) as resp:
        if resp.status != 200:
            # TODO: Better error handling/logging
            return []
        data = await resp.json()
        # Assume data is in the form of a dict with key "results" (adjust according to actual response)
        return data.get("results", [])

async def fetch_lei(session, company):
    # TODO: Implement a proper LEI lookup from an official registry.
    # This is a placeholder that simulates an external HTTP call.
    await asyncio.sleep(0.5)  # Simulate network delay
    if "Acme" in company.get("companyName", ""):
        return "529900T8BM49AURSDO55"
    return "Not Available"

async def process_entity(job_id, payload):
    # Process: Query Finnish Companies API, filter results, enrich with LEI.
    requested_at = datetime.datetime.utcnow().isoformat()
    async with aiohttp.ClientSession() as session:
        try:
            company_name = payload.get("companyName")
            # For now, filters are not processed; TODO: include filters processing if needed.
            filters = payload.get("filters", {})
            companies = await fetch_companies(session, company_name, filters)
            # TODO: Adapt filtering logic based on actual response structure.
            active_companies = [c for c in companies if c.get("status", "").lower() == "active"]
            enriched_results = []
            for company in active_companies:
                lei = await fetch_lei(session, company)
                enriched = {
                    "companyName": company.get("companyName", "Unknown"),
                    "businessId": company.get("businessId", "Unknown"),
                    "companyType": company.get("companyType", "Unknown"),
                    "registrationDate": company.get("registrationDate", "Unknown"),
                    "status": "Active",
                    "LEI": lei,
                }
                enriched_results.append(enriched)
            entity_jobs[job_id]["status"] = "success"
            entity_jobs[job_id]["results"] = enriched_results
            entity_jobs[job_id]["completedAt"] = datetime.datetime.utcnow().isoformat()
        except Exception as e:
            # TODO: Log exception details for debugging.
            entity_jobs[job_id]["status"] = "failure"
            entity_jobs[job_id]["error"] = str(e)

@app.route('/api/companies/search', methods=['POST'])
@validate_request(SearchRequest)  # Workaround: For POST, validation decorators are added after route decorator.
@validate_response(SearchResponse, 202)
async def search_companies(data: SearchRequest):
    # Fire and forget processing task using in-memory cache for a job.
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, data.__dict__))
    return jsonify({"searchId": job_id, "status": "processing", "requestedAt": requested_at}), 202

@app.route('/api/companies/results/<job_id>', methods=['GET'])
async def get_search_results(job_id):
    job = entity_jobs.get(job_id)
    if not job:
        abort(404, description="Job not found")
    if job["status"] == "processing":
        return jsonify({"searchId": job_id, "status": "processing"}), 202
    elif job["status"] == "failure":
        return jsonify({"searchId": job_id, "status": "failure", "error": job.get("error", "Unknown error")}), 500
    else:
        return jsonify({"searchId": job_id, "status": "success", "results": job.get("results", [])}), 200

@app.route('/api/companies/results', methods=['GET'])
async def list_search_jobs():
    jobs_list = []
    for job_id, details in entity_jobs.items():
        job_info = {"searchId": job_id, "status": details.get("status"), "requestedAt": details.get("requestedAt")}
        if "completedAt" in details:
            job_info["completedAt"] = details["completedAt"]
        jobs_list.append(job_info)
    return jsonify(jobs_list), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)