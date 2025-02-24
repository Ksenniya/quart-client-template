#!/usr/bin/env python3
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass, asdict

import aiohttp
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_response  # Workaround for POST endpoints

from common.config.config import ENTITY_VERSION  # Always use this constant
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

ENTITY_MODEL = "companies_jobs"  # Entity model name used in entity_service calls

# Startup initialization for external service
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Dataclass for POST request validation (only primitives are used)
@dataclass
class CompanyEnrichRequest:
    companyName: str
    filters: dict = None  # TODO: Consider refining filters schema if required

# Dataclass for POST response validation
@dataclass
class EnrichResponse:
    taskId: str
    message: str

# Workflow function applied to the job entity asynchronously before persistence.
# This function takes the job entity (which contains the submitted input data)
# as its only argument, performs the asynchronous enrichment tasks,
# and updates the entity state accordingly.
async def process_companies_jobs(entity):
    try:
        # Retrieve input data submitted with the job
        input_data = entity.get("input", {})
        company_name = input_data.get("companyName", "").strip()
        if not company_name:
            entity["status"] = "failed"
            entity["error"] = "companyName is required"
            entity["completedAt"] = datetime.utcnow().isoformat()
            return entity

        filters = input_data.get("filters") or {}

        # Step 1: Retrieve company data from the Finnish Companies Registry API
        async with aiohttp.ClientSession() as session:
            prh_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
            params = {"name": company_name}
            params.update(filters)
            try:
                async with session.get(prh_url, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        companies = data.get("results", [])
                    else:
                        companies = []
            except Exception as e:
                logger.error(f"Error calling PRH API: {e}")
                companies = []

        # If no companies are returned, simulate dummy data for prototype purposes.
        if not companies:
            companies = [
                {
                    "Company Name": company_name,
                    "Business ID": "1234567-8",
                    "Company Type": "OY",
                    "Registration Date": "2020-01-01",
                    "Status": "Active"
                },
                {
                    "Company Name": f"{company_name} Inactive",
                    "Business ID": "8765432-1",
                    "Company Type": "OY",
                    "Registration Date": "2019-01-01",
                    "Status": "Inactive"
                }
            ]

        # Step 2: Filter out inactive companies (active companies have Status == "Active")
        active_companies = [company for company in companies if company.get("Status") == "Active"]

        # Step 3: Enrich each active company with LEI data from an external API
        for company in active_companies:
            async with aiohttp.ClientSession() as session:
                lei_api_url = "https://example.com/lei"  # TODO: Replace with the real external LEI API endpoint.
                payload = {"businessId": company.get("Business ID")}
                try:
                    async with session.post(lei_api_url, json=payload, timeout=10) as resp:
                        if resp.status == 200:
                            lei_data = await resp.json()
                            company["LEI"] = lei_data.get("LEI", "Not Available")
                        else:
                            company["LEI"] = "Not Available"
                except Exception as e:
                    logger.error(f"Error calling LEI API: {e}")
                    company["LEI"] = "Not Available"
            if not company.get("LEI"):
                company["LEI"] = "LEI1234567890"  # Fallback LEI value for prototype

        # Step 4: Update the job entity with the enrichment results.
        entity["results"] = active_companies
        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat()
        entity["workflowProcessed"] = True

    except Exception as e:
        logger.exception("Error in workflow process_companies_jobs")
        entity["status"] = "failed"
        entity["error"] = str(e)
        entity["completedAt"] = datetime.utcnow().isoformat()
    return entity

# POST endpoint: Create job and process it using the workflow function.
@app.route('/companies/enrich', methods=['POST'])
@validate_request(CompanyEnrichRequest)  # For POST, validation is applied after the route decorator
@validate_response(EnrichResponse, 201)
async def enrich_companies(data: CompanyEnrichRequest):
    # Convert the validated dataclass to a dictionary.
    input_data = asdict(data)
    if not input_data.get("companyName"):
        return jsonify({"error": "companyName is required"}), 400

    requested_at = datetime.utcnow().isoformat()
    # Include input_data in the job entity so that the workflow function can access it.
    job_data = {
        "status": "processing",
        "requestedAt": requested_at,
        "input": input_data,
        "results": None
    }
    # Persist the job using the external entity_service with an attached workflow function.
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model=ENTITY_MODEL,
        entity_version=ENTITY_VERSION,  # Always use this constant
        entity=job_data,  # The job entity containing input data
        workflow=process_companies_jobs  # Workflow function applied asynchronously before persistence.
    )

    return EnrichResponse(taskId=job_id, message="Data retrieval and enrichment in progress or completed."), 201

# GET endpoint: Retrieve enriched results.
@app.route('/companies/results/<job_id>', methods=['GET'])
async def get_results(job_id):
    job = await entity_service.get_item(
        token=cyoda_token,
        entity_model=ENTITY_MODEL,
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        return jsonify({"error": "Task ID not found"}), 404

    return jsonify({
        "taskId": job_id,
        "status": job.get("status"),
        "requestedAt": job.get("requestedAt"),
        "completedAt": job.get("completedAt"),
        "results": job.get("results"),
        "error": job.get("error", None)
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)