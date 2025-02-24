#!/usr/bin/env python3
import asyncio
import uuid
from datetime import datetime
from dataclasses import dataclass, asdict

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response  # Workaround: for POST endpoints, validation decorators come after @app.route

from common.config.config import ENTITY_VERSION  # Always use this constant
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

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

# Workflow function to be applied to the job entity before persistence
async def process_companies_jobs(entity):
    # Modify job entity before persistence e.g. add createdAt timestamp and a workflow flag
    entity["workflowProcessed"] = True
    entity["createdAt"] = datetime.utcnow().isoformat()
    return entity

async def process_entity(job_id, input_data):
    """
    Process the data enrichment in background:
      • Calls the Finnish Companies Registry API.
      • Filters out inactive companies.
      • Enriches active companies with LEI data from an external API.
    """
    company_name = input_data.get("companyName")
    filters = input_data.get("filters") or {}

    # Step 1: Retrieve company data from the Finnish Companies Registry API
    async with aiohttp.ClientSession() as session:
        prh_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
        # Prepare query parameters: companyName and any additional filters.
        params = {"name": company_name}
        params.update(filters)  # TODO: Map additional filters to actual API query parameters if necessary.
        try:
            async with session.get(prh_url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Assuming data contains a "results" field with the companies list.
                    companies = data.get("results", [])
                else:
                    companies = []
        except Exception as e:
            print(f"Error calling PRH API: {e}")
            companies = []

    # For prototype purposes, if no companies are returned, simulate dummy data.
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

    # Step 3: Enrich each active company with LEI data
    for company in active_companies:
        async with aiohttp.ClientSession() as session:
            lei_api_url = "https://example.com/lei"  # TODO: Replace with the real external LEI API endpoint.
            # Mock request payload - using Business ID to search for the LEI.
            payload = {"businessId": company["Business ID"]}
            try:
                async with session.post(lei_api_url, json=payload) as resp:
                    if resp.status == 200:
                        lei_data = await resp.json()
                        company["LEI"] = lei_data.get("LEI", "Not Available")
                    else:
                        company["LEI"] = "Not Available"
            except Exception as e:
                print(f"Error calling LEI API: {e}")
                company["LEI"] = "Not Available"
        if not company.get("LEI"):
            company["LEI"] = "LEI1234567890"  # TODO: Replace with actual logic in production.

    # Step 4: Update the job status with the enriched results.
    # Retrieve the latest job data from the external service.
    job = await entity_service.get_item(
        token=cyoda_token,
        entity_model=ENTITY_MODEL,
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if job is None:
        # In case the job could not be retrieved, exit without failing.
        print(f"Job {job_id} not found during update.")
        return

    job["results"] = active_companies
    job["status"] = "completed"
    job["completedAt"] = datetime.utcnow().isoformat()

    await entity_service.update_item(
        token=cyoda_token,
        entity_model=ENTITY_MODEL,
        entity_version=ENTITY_VERSION,
        entity=job,
        meta={}
    )

# POST endpoint: Fire and forget processing task.
@app.route('/companies/enrich', methods=['POST'])
@validate_request(CompanyEnrichRequest)  # For POST, validation comes after route decorator (workaround)
@validate_response(EnrichResponse, 201)
async def enrich_companies(data: CompanyEnrichRequest):  # data is already validated as CompanyEnrichRequest
    # Convert dataclass to dict for further processing.
    input_data = asdict(data)
    if not input_data.get("companyName"):
        return jsonify({"error": "companyName is required"}), 400

    requested_at = datetime.utcnow().isoformat()
    job_data = {
        "status": "processing",
        "requestedAt": requested_at,
        "results": None
    }
    # Create a new job entry using the external entity_service with added workflow function
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model=ENTITY_MODEL,
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_data,  # the validated data object for job persistence
        workflow=process_companies_jobs  # Workflow function applied to the entity asynchronously before persistence.
    )

    # Fire and forget the background task.
    asyncio.create_task(process_entity(job_id, input_data))

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
        "results": job.get("results")
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)