#!/usr/bin/env python3
"""
Updated prototype.py – this version uses the new entity_service.add_item API,
which expects a workflow function as an additional parameter. The workflow function
(process_companies) is applied to the entity before it is persisted. In this example,
the POST endpoint merges the validated request data with an initial payload (including
a "processing" status and timestamp) and passes it to add_item with process_companies
as the workflow function. The process_companies function uses external APIs to enrich
the entity (it retrieves company data, filters active companies, enriches with LEI data,
and then updates the entity state) before it is saved. Clients can later query the job status
using the GET endpoint.
"""

import asyncio
import time
from dataclasses import dataclass

from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request, validate_response
import aiohttp

from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # initialize QuartSchema

# External API endpoint constants for the PRH API and LEI lookup
PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3"
COMPANY_ENDPOINT = f"{PRH_API_BASE}/companies"
LEI_API_BASE = "https://example.com/lei"  # TODO: Replace with an actual LEI data source

# --- App Startup ---
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# --- Dataclass Definitions for Validation ---
@dataclass
class CompanyQueryRequest:
    companyName: str
    outputFormat: str = "json"  # json or csv

@dataclass
class QueryResponse:
    jobId: str
    status: str
    requestedAt: str

# --- Helper Functions ---
async def get_prh_company_data(company_name: str):
    """
    Make an HTTP GET request to the Finnish Companies Registry API.
    """
    params = {"name": company_name}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(COMPANY_ENDPOINT, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data  # Adjust based on actual API response structure.
                else:
                    return {"error": f"PRH API returned status {resp.status}"}
        except Exception as e:
            return {"error": str(e)}

async def get_lei_for_company(company):
    """
    Retrieve the LEI for the given company.
    Placeholder implementation – replace with an actual API call as needed.
    """
    async with aiohttp.ClientSession() as session:
        try:
            await asyncio.sleep(0.1)  # Simulate network delay
            return "MOCK_LEI_12345"
        except Exception:
            return "Not Available"

async def process_companies(entity: dict) -> dict:
    """
    Workflow function applied to the 'companies' entity before persistence.
    It performs the following actions:
      - Validates that companyName exists in the entity.
      - Retrieves company data from the PRH API.
      - Filters for active companies.
      - Enriches active companies by adding LEI data.
      - Updates entity state to "completed" or "failed" accordingly.
      
    This function returns the mutated entity which will then be persisted.
    """
    # The entity is expected to include the original request data.
    company_name = entity.get("companyName")
    if not company_name:
        entity["status"] = "failed"
        entity["error"] = "companyName is required"
        return entity

    prh_data = await get_prh_company_data(company_name)
    if isinstance(prh_data, dict) and prh_data.get("error"):
        entity["status"] = "failed"
        entity["error"] = prh_data["error"]
        return entity

    # Extract list of companies from the API response.
    companies = prh_data.get("results", [])

    # Filter out inactive companies (assuming 'status' indicates activity).
    active_companies = [c for c in companies if c.get("status", "").lower() == "active"]

    # Enrich each active company with LEI data.
    enriched_companies = []
    for comp in active_companies:
        lei = await get_lei_for_company(comp)
        enriched_company = {
            "companyName": comp.get("name", "Unknown"),
            "businessId": comp.get("businessId", "Unknown"),
            "companyType": comp.get("companyForm", "Unknown"),
            "registrationDate": comp.get("registrationDate", "Unknown"),
            "status": comp.get("status", "Unknown"),
            "lei": lei if lei else "Not Available"
        }
        enriched_companies.append(enriched_company)

    # Update entity with the results.
    entity["status"] = "completed"
    entity["completedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    entity["results"] = enriched_companies
    return entity

# --- Endpoints ---
@app.route('/companies/query', methods=['POST'])
@validate_request(CompanyQueryRequest)
@validate_response(QueryResponse, 202)
async def company_query(data: CompanyQueryRequest):
    """
    POST endpoint that triggers external API calls for company queries.
    The endpoint creates a new job record via entity_service.add_item. The new API
    expects a workflow function (process_companies) to be passed, which is applied to
    the entity (job record) before it is persisted. The updated entity will contain
    the processing status, enrichment results, or error information.
    """
    requested_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    # Merge the validated request data (e.g. companyName, outputFormat) with an initial payload.
    # This entity will be processed by the workflow function.
    initial_data = {
        "companyName": data.companyName,
        "outputFormat": data.outputFormat,
        "status": "processing",
        "requestedAt": requested_at
    }
    # Create a new job record in the external service.
    # The workflow function process_companies will be applied to the entity before persistence.
    technical_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=initial_data,  # the initial job payload (includes request data)
        workflow=process_companies  # workflow function applied to the entity
    )
    return QueryResponse(jobId=technical_id, status="processing", requestedAt=requested_at), 202

@app.route('/companies/result/<job_id>', methods=['GET'])
async def get_result(job_id: str):
    """
    GET endpoint that returns the processed results for a given job_id.
    The result is retrieved via entity_service.get_item.
    """
    result = await entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not result:
        return jsonify({"error": "Job ID not found"}), 404

    # Optionally include the job_id in the response.
    result["jobId"] = job_id
    return jsonify(result)

# --- Main ---
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)