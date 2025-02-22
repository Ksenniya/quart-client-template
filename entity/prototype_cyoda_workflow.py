#!/usr/bin/env python3
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response
from dataclasses import dataclass
import aiohttp
import asyncio
import uuid
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
async def process_companies(entity):
    # Add workflow specific modifications to the entity.
    entity["workflowProcessed"] = True
    entity["processedAtWorkFlow"] = datetime.utcnow().isoformat()
    return entity

# Processing task that retrieves and enriches data.
async def process_entity(job_id, task_data: dict):
    requested_at = datetime.utcnow().isoformat()
    try:
        company_name = task_data.get("companyName")
        page = task_data.get("page", 1)
        async with aiohttp.ClientSession() as session:
            companies_response = await fetch_companies_data(session, company_name, page)
            if companies_response is None:
                update_data = {
                    "status": "failed",
                    "error": "Failed to retrieve data from Finnish Companies Registry API"
                }
                entity_service.update_item(
                    token=cyoda_token,
                    entity_model="companies",
                    entity_version=ENTITY_VERSION,
                    entity=update_data,
                    meta={"technical_id": job_id}
                )
                return

            # TODO: Process companies_response based on the actual API response structure.
            companies_list = companies_response.get("results", [])
            # Filter active companies; assume each company dict has a "status" field with value "active" if active.
            active_companies = [comp for comp in companies_list if comp.get("status", "").lower() == "active"]

            enriched_results = []
            for comp in active_companies:
                lei = await fetch_lei(session, comp)
                # TODO: Map actual fields from the API response to your output model.
                enriched_results.append({
                    "companyName": comp.get("name", "Unknown"),
                    "businessId": comp.get("businessId", "Unknown"),
                    "companyType": comp.get("companyForm", "Unknown"),
                    "registrationDate": comp.get("registrationDate", "Unknown"),
                    "status": "Active",
                    "LEI": lei,
                })
            # Update job completion status.
            update_data = {
                "status": "completed",
                "data": enriched_results,
                "requestedAt": requested_at,
                "completedAt": datetime.utcnow().isoformat()
            }
            entity_service.update_item(
                token=cyoda_token,
                entity_model="companies",
                entity_version=ENTITY_VERSION,
                entity=update_data,
                meta={"technical_id": job_id}
            )
    except Exception as e:
        update_data = {
            "status": "failed",
            "error": str(e)
        }
        entity_service.update_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            entity=update_data,
            meta={"technical_id": job_id}
        )

# Workaround for quart-schema issue: For POST methods, route decorator comes first then validation decorators.
@app.route('/companies/search', methods=['POST'])
@validate_request(CompanySearch)
@validate_response(CompanySearchResponse, 201)
async def companies_search(data: CompanySearch):
    requested_at = datetime.utcnow().isoformat()
    # Create initial job data.
    job_data = {"status": "processing", "requestedAt": requested_at}
    # Add the job record to the external entity service with a workflow function.
    job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        entity=job_data,
        workflow=process_companies
    )
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, data.__dict__))
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