#!/usr/bin/env python3
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response
from dataclasses import dataclass
import aiohttp
import asyncio
from datetime import datetime
import random

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)  # Enable QuartSchema once as required.

# Startup initialization.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Dataclass for POST request validation.
@dataclass
class CompanySearch:
    companyName: str
    page: int = 1
    # TODO: Additional filters can be added as needed.

# Dataclass for POST response validation.
@dataclass
class CompanySearchResponse:
    taskId: str
    status: str

# Helper function to retrieve company data from the Finnish Companies Registry API.
async def fetch_companies_data(session, company_name, page=1):
    # TODO: Expand query parameters based on additional filters if needed.
    url = f"https://avoindata.prh.fi/opendata-ytj-api/v3/companies?name={company_name}&page={page}"
    async with session.get(url) as resp:
        if resp.status != 200:
            # TODO: Handle error more gracefully.
            return None
        return await resp.json()

# Helper function to simulate LEI lookup for a given company.
async def fetch_lei(session, company):
    # TODO: Implement actual LEI data retrieval from an official source.
    await asyncio.sleep(0.1)  # Simulate network delay
    if random.choice([True, False]):
        return "MOCK-LEI-1234567890"
    else:
        return "Not Available"

# Workflow function applied to "companies" entity before persistence.
# All processing logic is moved here.
async def process_companies(entity):
    # Expecting that entity contains the search parameters.
    company_name = entity.get("companyName")
    page = entity.get("page", 1)
    try:
        async with aiohttp.ClientSession() as session:
            companies_response = await fetch_companies_data(session, company_name, page)
            if companies_response is None:
                entity["status"] = "failed"
                entity["error"] = "Failed to retrieve data from Finnish Companies Registry API"
                return entity

            # Process companies_response based on the actual API response structure.
            companies_list = companies_response.get("results", [])
            # Filter active companies; assume each company dict has a "status" field with value "active" if active.
            active_companies = [comp for comp in companies_list if comp.get("status", "").lower() == "active"]

            enriched_results = []
            for comp in active_companies:
                lei = await fetch_lei(session, comp)
                # Map actual fields from the API response to your output model.
                enriched_results.append({
                    "companyName": comp.get("name", "Unknown"),
                    "businessId": comp.get("businessId", "Unknown"),
                    "companyType": comp.get("companyForm", "Unknown"),
                    "registrationDate": comp.get("registrationDate", "Unknown"),
                    "status": "Active",
                    "LEI": lei,
                })
            # Update job completion status.
            entity.update({
                "status": "completed",
                "data": enriched_results,
                "completedAt": datetime.utcnow().isoformat()
            })
    except Exception as e:
        entity["status"] = "failed"
        entity["error"] = str(e)
    # Additional workflow modifications.
    entity["workflowProcessed"] = True
    entity["processedAtWorkFlow"] = datetime.utcnow().isoformat()
    return entity

# Endpoint for companies search.
@app.route('/companies/search', methods=['POST'])
@validate_request(CompanySearch)
@validate_response(CompanySearchResponse, 201)
async def companies_search(data: CompanySearch):
    requested_at = datetime.utcnow().isoformat()
    # Create initial job data including parameters needed by the workflow.
    job_data = {
        "status": "processing",
        "requestedAt": requested_at,
        "companyName": data.companyName,
        "page": data.page
    }
    # Add the job record to the external entity service with a workflow function.
    # The workflow function (process_companies) will be applied asynchronously before persisting.
    job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        entity=job_data,
        workflow=process_companies
    )
    return jsonify({"taskId": job_id, "status": "submitted"}), 201

@app.route('/companies/results/<job_id>', methods=['GET'])
async def companies_results(job_id):
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        abort(404, description="Task not found")
    return jsonify(job)

@app.route('/companies/results/<job_id>/status', methods=['GET'])
async def companies_status(job_id):
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        abort(404, description="Task not found")
    return jsonify({"taskId": job_id, "status": job.get("status")})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)