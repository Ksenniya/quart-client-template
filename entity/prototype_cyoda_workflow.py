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
    try:
        await init_cyoda(cyoda_token)
    except Exception as e:
        # Prevent startup failure if initialization fails.
        app.logger.error(f"Failed to initialize cyoda: {e}")
        raise

# Dataclass for POST request validation.
@dataclass
class CompanySearch:
    companyName: str
    page: int = 1
    # Additional filters can be added as needed.

# Dataclass for POST response validation.
@dataclass
class CompanySearchResponse:
    taskId: str
    status: str

# Helper function to retrieve company data from the Finnish Companies Registry API.
async def fetch_companies_data(session: aiohttp.ClientSession, company_name: str, page: int = 1):
    # Expand query parameters based on additional filters if needed.
    url = f"https://avoindata.prh.fi/opendata-ytj-api/v3/companies?name={company_name}&page={page}"
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                # Log error and return None to indicate failure.
                app.logger.error(f"Finnish Companies Registry API returned status {resp.status} for URL: {url}")
                return None
            return await resp.json()
    except Exception as e:
        app.logger.error(f"Exception during fetching companies data: {e}")
        return None

# Helper function to simulate LEI lookup for a given company.
async def fetch_lei(session: aiohttp.ClientSession, company: dict):
    # Simulate network delay and potential lookup
    try:
        await asyncio.sleep(0.1)
        # Randomly simulate LEI availability.
        if random.choice([True, False]):
            return "MOCK-LEI-1234567890"
        else:
            return "Not Available"
    except Exception as e:
        app.logger.error(f"Exception during LEI lookup: {e}")
        return "Not Available"

# Workflow function applied to "companies" entity before persistence.
# All heavy processing logic is moved here to free the controller.
async def process_companies(entity: dict):
    # The entity is expected to have the search parameters.
    company_name = entity.get("companyName")
    page = entity.get("page", 1)
    # Set default timestamps if not already present.
    requested_at = entity.get("requestedAt", datetime.utcnow().isoformat())
    try:
        async with aiohttp.ClientSession() as session:
            companies_response = await fetch_companies_data(session, company_name, page)
            if companies_response is None:
                # Mark failure with error details.
                entity["status"] = "failed"
                entity["error"] = "Failed to retrieve data from Finnish Companies Registry API"
                entity["completedAt"] = datetime.utcnow().isoformat()
                # Early return with modified entity that will be persisted.
                return entity

            # Process companies_response based on the actual API response structure.
            companies_list = companies_response.get("results", [])
            # Filter active companies; assume each company dict has a "status" field with value "active".
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

            # Update entity with enriched results and mark it as completed.
            entity.update({
                "status": "completed",
                "data": enriched_results,
                "requestedAt": requested_at,
                "completedAt": datetime.utcnow().isoformat()
            })
    except Exception as e:
        # Catch and log any exceptions during processing.
        app.logger.error(f"Exception in process_companies workflow: {e}")
        entity["status"] = "failed"
        entity["error"] = str(e)
        entity["completedAt"] = datetime.utcnow().isoformat()

    # Mark that workflow processing has been applied.
    entity["workflowProcessed"] = True
    entity["processedAtWorkFlow"] = datetime.utcnow().isoformat()
    return entity

# Endpoint for companies search.
@app.route('/companies/search', methods=['POST'])
@validate_request(CompanySearch)
@validate_response(CompanySearchResponse, 201)
async def companies_search(data: CompanySearch):
    # Capture request time and parameters.
    requested_at = datetime.utcnow().isoformat()
    # Create initial job data with search parameters.
    job_data = {
        "status": "processing",
        "requestedAt": requested_at,
        "companyName": data.companyName,
        "page": data.page
    }
    # Add the job record to the external entity service with a workflow function.
    # The workflow function (process_companies) will run asynchronously and modify the entity.
    try:
        job_id = entity_service.add_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            entity=job_data,
            workflow=process_companies
        )
    except Exception as e:
        app.logger.error(f"Error adding item to entity_service: {e}")
        abort(500, description="Failed to create job")
    return jsonify({"taskId": job_id, "status": "submitted"}), 201

# Endpoint to fetch complete results of a companies job.
@app.route('/companies/results/<job_id>', methods=['GET'])
async def companies_results(job_id: str):
    try:
        job = entity_service.get_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
    except Exception as e:
        app.logger.error(f"Error fetching job {job_id}: {e}")
        abort(500, description="Error retrieving task")
    if not job:
        abort(404, description="Task not found")
    return jsonify(job)

# Endpoint to check status of a companies job.
@app.route('/companies/results/<job_id>/status', methods=['GET'])
async def companies_status(job_id: str):
    try:
        job = entity_service.get_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
    except Exception as e:
        app.logger.error(f"Error fetching status for job {job_id}: {e}")
        abort(500, description="Error retrieving task status")
    if not job:
        abort(404, description="Task not found")
    # Return only taskId and status.
    return jsonify({"taskId": job_id, "status": job.get("status")})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)