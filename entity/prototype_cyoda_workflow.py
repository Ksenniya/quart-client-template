#!/usr/bin/env python3
import asyncio
import datetime
import json
from dataclasses import dataclass

from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response  # For POST, route decorator comes first, then validators.
import aiohttp

from common.config.config import ENTITY_VERSION  # Use this constant for all entity_service calls
from app_init.app_init import cyoda_token, entity_service
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Define entity model name for the search jobs
ENTITY_MODEL = "company_search_job"

# Data validation models
@dataclass
class SearchRequest:
    companyName: str
    # Optional filters field if needed
    filters: dict = None  # default to None if not provided

@dataclass
class SearchResponse:
    searchId: str
    status: str
    requestedAt: str

# Constants for external API endpoints
FINNISH_API_URL = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
LEI_API_URL = "https://example.com/lei-lookup"  # Placeholder URL

async def fetch_companies(session: aiohttp.ClientSession, company_name: str, filters: dict):
    # Construct query parameters: currently using only companyName
    params = {"name": company_name}
    # If any filters are provided, add them to the params (prevent accidental None)
    if filters:
        params.update(filters)
    try:
        async with session.get(FINNISH_API_URL, params=params, timeout=10) as resp:
            if resp.status != 200:
                # In case of non-200, return empty list (or consider raising exception)
                return []
            data = await resp.json()
            # Assume the response data has a "results" key; adjust accordingly if needed.
            return data.get("results", [])
    except Exception:
        return []

async def fetch_lei(session: aiohttp.ClientSession, company: dict):
    # This is a placeholder implementation that simulates a network call.
    try:
        # Simulate network delay
        await asyncio.sleep(0.5)
        # Dummy logic for demonstration: if company name contains "Acme", return a dummy LEI.
        if "Acme" in company.get("companyName", ""):
            return "529900T8BM49AURSDO55"
    except Exception:
        pass
    return "Not Available"

# Workflow function that processes the search job entity before it is persisted.
# All asynchronous tasks (like fetching companies and LEI) are handled here,
# freeing the controller from any excessive logic.
async def process_company_search_job(entity: dict):
    # This workflow function runs before persistence and updates the entity in memory.
    async with aiohttp.ClientSession() as session:
        try:
            payload = entity.get("payload", {})
            company_name = payload.get("companyName")
            if not company_name:
                raise ValueError("Missing companyName in payload")
            filters = payload.get("filters", {}) or {}
            companies = await fetch_companies(session, company_name, filters)
            # Filter companies: example filtering for those with "active" status.
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
            # Update the entity state; do not call any external entity service functions!
            entity["status"] = "success"
            entity["results"] = enriched_results
            entity["completedAt"] = datetime.datetime.utcnow().isoformat()
        except Exception as e:
            entity["status"] = "failure"
            entity["error"] = str(e)
    # Return the in-memory modified entity which will be persisted.
    return entity

@app.route('/api/companies/search', methods=['POST'])
@validate_request(SearchRequest)  # Validation on input data.
@validate_response(SearchResponse, 202)
async def search_companies(data: SearchRequest):
    # Capture the timestamp when the request was received.
    requested_at = datetime.datetime.utcnow().isoformat()
    # Prepare the search job data including the payload received from the client.
    job_data = {
        "status": "processing",
        "requestedAt": requested_at,
        "payload": data.__dict__
    }
    # Use the external service to add a new search job.
    # The workflow function process_company_search_job is applied asynchronously
    # before the entity is persisted, handling all required asynchronous tasks.
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model=ENTITY_MODEL,
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_data,  # job data including search parameters
        workflow=process_company_search_job  # Workflow applied asynchronously before persistence.
    )
    return jsonify({"searchId": job_id, "status": "processing", "requestedAt": requested_at}), 202

@app.route('/api/companies/results/<job_id>', methods=['GET'])
async def get_search_results(job_id: str):
    # Retrieve job details via the external service.
    job = await entity_service.get_item(
        token=cyoda_token,
        entity_model=ENTITY_MODEL,
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        abort(404, description="Job not found")
    # Return appropriate response based on job status.
    if job.get("status") == "processing":
        return jsonify({"searchId": job_id, "status": "processing"}), 202
    elif job.get("status") == "failure":
        return jsonify({
            "searchId": job_id,
            "status": "failure",
            "error": job.get("error", "Unknown error")
        }), 500
    else:
        return jsonify({
            "searchId": job_id,
            "status": "success",
            "results": job.get("results", [])
        }), 200

@app.route('/api/companies/results', methods=['GET'])
async def list_search_jobs():
    # Retrieve a list of all search jobs via the external service.
    jobs_list = await entity_service.get_items(
        token=cyoda_token,
        entity_model=ENTITY_MODEL,
        entity_version=ENTITY_VERSION,
    )
    return jsonify(jobs_list), 200

@app.before_serving
async def startup():
    # Initialize external cyoda repository before serving.
    await init_cyoda(cyoda_token)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)