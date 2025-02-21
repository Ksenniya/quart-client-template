Below is one valid answer. In this refactored version the local “job_results” dictionary and manual UUID/counters are removed. Instead, when a new job is started the POST endpoint calls the external entity_service.add_item (using the entity_model "companies" and ENTITY_VERSION) passing an initial payload (with status “processing” and a requestedAt timestamp). The returned technical id is then returned to the caller so they can later query the job status. In the background processing task (process_query) any errors or successful results are updated via an entity_service.update_item call (passing a meta dict containing the “technical_id”). Finally, the GET endpoint calls the external entity_service.get_item by that same id. Note that the startup procedure is also added exactly as required.

Below is the complete updated prototype.py:

------------------------------------------------------------
#!/usr/bin/env python3
"""
Updated prototype.py – this version replaces local in‑memory storage with calls to
an external service (entity_service) to create, update and query job results.
"""

from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response
import aiohttp
import asyncio
import time
import uuid

from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # initialize QuartSchema

# External API endpoint constants for the PRH API and LEI lookup
PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3"
COMPANY_ENDPOINT = f"{PRH_API_BASE}/companies"
LEI_API_BASE = "https://example.com/lei"  # TODO: Integrate with an actual LEI data source

# --- App Startup: Initialize Cyoda before serving ---
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

# --- Helper functions ---
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
                    return data  # TODO: Adjust based on actual API response structure.
                else:
                    return {"error": f"PRH API returned status {resp.status}"}
        except Exception as e:
            return {"error": str(e)}

async def get_lei_for_company(company):
    """
    Retrieve the LEI for the given company.
    Placeholder implementation – TODO: Replace with an actual API call.
    """
    async with aiohttp.ClientSession() as session:
        try:
            await asyncio.sleep(0.1)  # Simulate network delay
            return "MOCK_LEI_12345"
        except Exception:
            return "Not Available"

async def process_query(technical_id: str, payload: dict):
    """
    Retrieve company data from the PRH API, filter inactive companies,
    enrich with LEI data and update the job result via entity_service.
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

    # TODO: Adjust this extraction based on the actual API response structure.
    companies = prh_data.get("results", [])

    # 2. Filter out inactive companies (assuming 'status' field holds the value)
    active_companies = [c for c in companies if c.get("status", "").lower() == "active"]

    # 3. Enrich each active company with LEI data.
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
    POST endpoint that triggers external API calls, filtering and enrichment.
    Instead of using a local cache, this endpoint creates a record via entity_service.
    """
    requested_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    # Initial job data payload
    initial_data = {
        "status": "processing",
        "requestedAt": requested_at
    }
    # Create a new item in the external entity_service and retrieve its technical id.
    technical_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        entity=initial_data
    )

    # Fire-and-forget the async task to process the query – the job identified by technical_id will be updated.
    asyncio.create_task(process_query(technical_id, data.__dict__))

    return QueryResponse(jobId=technical_id, status="processing", requestedAt=requested_at), 202

@app.route('/companies/result/<job_id>', methods=['GET'])
async def get_result(job_id: str):
    """
    GET endpoint that returns the processed results for the given job_id.
    Instead of reading from local in‑memory storage, we retrieve it via entity_service.
    """
    result = await entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not result:
        return jsonify({"error": "Job ID not found"}), 404

    # Optionally include the job_id in the response for clarity.
    result["jobId"] = job_id
    return jsonify(result)

# --- Main ---
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

------------------------------------------------------------

Explanation:

1. In the POST endpoint (/companies/query), a new job record is created via entity_service.add_item. Its returned technical_id is then both used to later update the record in process_query and is returned to the client.

2. The process_query function now calls entity_service.update_item instead of writing to a local dictionary. It updates either on error or upon successful processing.

3. The GET endpoint (/companies/result/<job_id>) now calls entity_service.get_item using the provided id (technical_id).

4. A startup function has been added which calls init_cyoda with the cyoda_token before the server starts serving requests.

This approach preserves the original business logic (data ingestion from external APIs, filtering, enrichment, etc.) while replacing local caching with calls to an external storage service (entity_service).