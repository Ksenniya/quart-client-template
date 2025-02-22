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
    # TODO: Add a 'filters' field once requirements are clarified (e.g., Optional[dict]) using primitive types if possible.

@dataclass
class SearchResponse:
    searchId: str
    status: str
    requestedAt: str

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
            update_data = {
                "status": "success",
                "results": enriched_results,
                "completedAt": datetime.datetime.utcnow().isoformat()
            }
            await entity_service.update_item(
                token=cyoda_token,
                entity_model=ENTITY_MODEL,
                entity_version=ENTITY_VERSION,
                entity=update_data,
                meta={"technical_id": job_id}
            )
        except Exception as e:
            update_data = {
                "status": "failure",
                "error": str(e)
            }
            await entity_service.update_item(
                token=cyoda_token,
                entity_model=ENTITY_MODEL,
                entity_version=ENTITY_VERSION,
                entity=update_data,
                meta={"technical_id": job_id}
            )

@app.route('/api/companies/search', methods=['POST'])
@validate_request(SearchRequest)  # Workaround: For POST, validation decorators are added after route decorator.
@validate_response(SearchResponse, 202)
async def search_companies(data: SearchRequest):
    # Instead of using local in-memory cache, we use an external entity_service.
    requested_at = datetime.datetime.utcnow().isoformat()
    job_data = {"status": "processing", "requestedAt": requested_at}
    # Use external service to add a new search job; the returned id will be used to query the job.
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model=ENTITY_MODEL,
        entity_version=ENTITY_VERSION,
        entity=job_data
    )
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, data.__dict__))
    return jsonify({"searchId": job_id, "status": "processing", "requestedAt": requested_at}), 202

@app.route('/api/companies/results/<job_id>', methods=['GET'])
async def get_search_results(job_id):
    # Retrieve job details via external service.
    job = await entity_service.get_item(
        token=cyoda_token,
        entity_model=ENTITY_MODEL,
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        abort(404, description="Job not found")
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
    # Retrieve all search jobs via external service.
    jobs_list = await entity_service.get_items(
        token=cyoda_token,
        entity_model=ENTITY_MODEL,
        entity_version=ENTITY_VERSION,
    )
    return jsonify(jobs_list), 200

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)