#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response  # Issue workaround: for POST, route decorator must come first, then validate_request then validate_response.
import aiohttp

from common.config.config import ENTITY_VERSION
from app_init.app_init import cyoda_token, entity_service
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Enable QuartSchema

# Data classes for request and response payloads
@dataclass
class FinnishCompanyQuery:
    companyName: str
    location: Optional[str] = None
    registrationDateStart: Optional[str] = None
    registrationDateEnd: Optional[str] = None

@dataclass
class QueryResponse:
    queryId: str
    status: str
    requestedAt: str

# Workflow function applied to the entity asynchronously before persistence.
# All processing logic from the controller can be moved into this function.
async def process_finnish_company_query(entity: dict) -> dict:
    # Retrieve the query parameters stored in the entity
    query_data = entity.get("queryParams", {})
    async with aiohttp.ClientSession() as session:
        finnish_api_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
        params = {"name": query_data.get("companyName")}
        if query_data.get("location"):
            params["location"] = query_data["location"]
        if query_data.get("registrationDateStart"):
            params["registrationDateStart"] = query_data["registrationDateStart"]
        if query_data.get("registrationDateEnd"):
            params["registrationDateEnd"] = query_data["registrationDateEnd"]
        try:
            async with session.get(finnish_api_url, params=params) as resp:
                if resp.status != 200:
                    entity["status"] = "error"
                    entity["results"] = {"error": "Failed to retrieve data from Finnish API"}
                    entity["completedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
                    return entity
                finnish_data = await resp.json()
        except Exception as e:
            entity["status"] = "error"
            entity["results"] = {"error": str(e)}
            entity["completedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
            return entity

        companies: List[Dict[str, Any]] = finnish_data.get("results", [])
        active_companies = []
        for company in companies:
            if company.get("status", "").lower() == "active":
                active_companies.append(company)

        tasks = [fetch_and_enrich_lei(session, company) for company in active_companies]
        enriched_companies = await asyncio.gather(*tasks)

        results = []
        for comp in enriched_companies:
            results.append({
                "companyName": comp.get("companyName", "Unknown"),
                "businessId": comp.get("businessId", "Unknown"),
                "companyType": comp.get("companyType", "Unknown"),
                "registrationDate": comp.get("registrationDate", "Unknown"),
                "status": comp.get("status", "Unknown"),
                "LEI": comp.get("LEI", "Not Available"),
            })

        entity["status"] = "completed"
        entity["results"] = results
        entity["completedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
        return entity

# Startup: initialize cyoda integration
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# POST endpoint: create company query.
@app.route('/api/finnish-companies', methods=['POST'])
@validate_request(FinnishCompanyQuery)
@validate_response(QueryResponse, 200)
async def create_company_query(data: FinnishCompanyQuery):
    # Generate a unique identifier and timestamp
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat() + "Z"
    # Create initial job data and include query parameters for later processing
    job_data = {
        "queryId": job_id,
        "status": "processing",
        "requestedAt": requested_at,
        "results": None,
        "queryParams": data.__dict__
    }
    # Add job to external entity service with workflow function.
    # The workflow function (process_finnish_company_query) will run asynchronously,
    # perform all external API calls and enrichment, modify the job_data and the new state will be persisted.
    stored_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="finnish_company_query",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_data,
        workflow=process_finnish_company_query  # Workflow function applied to the entity asynchronously before persistence.
    )
    return QueryResponse(queryId=stored_id, status="processing", requestedAt=requested_at)

# GET endpoint: get query results.
@app.route('/api/results/<job_id>', methods=['GET'])
async def get_query_results(job_id: str):
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="finnish_company_query",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        abort(404, description="Query ID not found")
    return jsonify(job)

# External LEI enrichment using aiohttp.
async def fetch_and_enrich_lei(session: aiohttp.ClientSession, company: dict) -> dict:
    lei_api_url = "http://example.com/lei"  # Placeholder URL
    params = {"businessId": company.get("businessId")}
    try:
        async with session.get(lei_api_url, params=params) as resp:
            if resp.status == 200:
                lei_data = await resp.json()
                company["LEI"] = lei_data.get("LEI", "Not Available")
            else:
                company["LEI"] = "Not Available"
    except Exception:
        company["LEI"] = "Not Available"
    return company

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)