#!/usr/bin/env python3
"""
Updated prototype.py – this version now uses the new entity_service.add_item API,
which expects an additional workflow function to be applied to the entity before it is persisted.
In this implementation, the POST endpoint creates a job record (for "companies") using add_item,
passing process_companies as the workflow function. The workflow function (process_companies)
retrieves and processes data from the external Finnish Companies Registry API, enriches the results,
and then updates the job record via entity_service.update_item.
"""

from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response
import aiohttp
import asyncio
import time

from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # initialize QuartSchema

# Constants for external APIs
PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3"
COMPANY_ENDPOINT = f"{PRH_API_BASE}/companies"
LEI_API_BASE = "https://example.com/lei"  # TODO: Replace with actual LEI lookup URL when available

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
    Make an HTTP GET request to the Finnish Companies Registry API using aiohttp.
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

async def process_companies(technical_id: str, payload: dict):
    """
    Workflow function: Retrieve company data from the PRH API, filter inactive companies,
    enrich active companies with LEI data, and update the job record via entity_service.
    """
    company_name = payload.get("companyName")
    if not company_name:
        update_data = {"status": "failed", "error": "companyName is required"}
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            entity=update_data,
            meta={"technical_id": technical_id}
        )
        return

    # 1. Retrieve data from the Finnish Companies Registry API
    prh_data = await get_prh_company_data(company_name)
    if isinstance(prh_data, dict) and prh_data.get("error"):
        update_data = {"status": "failed", "error": prh_data["error"]}
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            entity=update_data,
            meta={"technical_id": technical_id}
        )
        return

    # Extract companies from API response – adjust if necessary.
    companies = prh_data.get("results", [])

    # 2. Filter out inactive companies based on 'status'
    active_companies = [c for c in companies if c.get("status", "").lower() == "active"]

    # 3. Enrich active companies with LEI data.
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

    # Update the final result via entity_service
    update_data = {
        "status": "completed",
        "completedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "results": enriched_companies
    }
    await entity_service.update_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        entity=update_data,
        meta={"technical_id": technical_id}
    )

# --- Endpoints ---
@app.route('/companies/query', methods=['POST'])
@validate_request(CompanyQueryRequest)
@validate_response(QueryResponse, 202)
async def company_query(data: CompanyQueryRequest):
    """
    POST endpoint that triggers external API calls for company queries.
    A new job record is created via entity_service.add_item, with the workflow function process_companies.
    The technical_id returned is used for further updates and for client queries.
    """
    requested_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    # Initial payload for the job record.
    initial_data = {
        "status": "processing",
        "requestedAt": requested_at
    }
    # Create a new item in the external entity service, providing the workflow function.
    technical_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        entity=initial_data,
        workflow=process_companies
    )
    # With the new API, the workflow (process_companies) will be applied automatically.
    return QueryResponse(jobId=technical_id, status="processing", requestedAt=requested_at), 202

@app.route('/companies/result/<job_id>', methods=['GET'])
async def get_result(job_id: str):
    """
    GET endpoint that returns the processed results for the given job_id.
    The result is retrieved using entity_service.get_item.
    """
    result = await entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not result:
        return jsonify({"error": "Job ID not found"}), 404

    # Include jobId in the response for clarity.
    result["jobId"] = job_id
    return jsonify(result)

# --- Main ---
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)