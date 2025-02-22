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

# Remove local in‑memory storage usage; all data is now stored in external entity service.

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

# Startup: initialize cyoda integration
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# POST endpoint: create company query.
@app.route('/api/finnish-companies', methods=['POST'])
@validate_request(FinnishCompanyQuery)  # For POST, validate_request goes after route decorator.
@validate_response(QueryResponse, 200)     # For POST, validate_response comes next.
async def create_company_query(data: FinnishCompanyQuery):
    # Generate a unique identifier and timestamp
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat() + "Z"
    # Create initial job data
    job_data = {
        "queryId": job_id,
        "status": "processing",
        "requestedAt": requested_at,
        "results": None
    }
    # Add job to external entity service
    stored_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="finnish_company_query",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_data  # the initial job data
    )
    # Fire and forget the processing task; pass the job data as well.
    asyncio.create_task(process_entity(stored_id, job_data, data.__dict__))
    return QueryResponse(queryId=stored_id, status="processing", requestedAt=requested_at)

# GET endpoint: get query results.
@app.route('/api/results/<job_id>', methods=['GET'])
async def get_query_results(job_id: str):
    # Retrieve the job from the external entity service
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="finnish_company_query",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        abort(404, description="Query ID not found")
    return jsonify(job)

# Processing task: calls external APIs and aggregates results.
async def process_entity(job_id: str, job_data: dict, query_data: dict):
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
                    job_data["status"] = "error"
                    job_data["results"] = {"error": "Failed to retrieve data from Finnish API"}
                    job_data["completedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
                    entity_service.update_item(
                        token=cyoda_token,
                        entity_model="finnish_company_query",
                        entity_version=ENTITY_VERSION,  # always use this constant
                        entity=job_data,
                        meta={}
                    )
                    return
                finnish_data = await resp.json()
        except Exception as e:
            job_data["status"] = "error"
            job_data["results"] = {"error": str(e)}
            job_data["completedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
            entity_service.update_item(
                token=cyoda_token,
                entity_model="finnish_company_query",
                entity_version=ENTITY_VERSION,  # always use this constant
                entity=job_data,
                meta={}
            )
            return

        # Assuming a 'results' list is provided in the finnish API response.
        companies: List[Dict[str, Any]] = finnish_data.get("results", [])

        # Filter out inactive companies.
        active_companies = []
        for company in companies:
            if company.get("status", "").lower() == "active":
                active_companies.append(company)

        # Enrich each active company with LEI information.
        tasks = [fetch_and_enrich_lei(session, company) for company in active_companies]
        enriched_companies = await asyncio.gather(*tasks)

        # Format the final results with required fields.
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

        job_data["status"] = "completed"
        job_data["results"] = results
        job_data["completedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
        entity_service.update_item(
            token=cyoda_token,
            entity_model="finnish_company_query",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=job_data,
            meta={}
        )

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