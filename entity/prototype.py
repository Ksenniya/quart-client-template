#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response  # Issue workaround: for POST, route decorator must come first, then validate_request then validate_response.
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # Enable QuartSchema

# In-memory storage for job results
entity_jobs: Dict[str, Dict[str, Any]] = {}


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


# POST endpoint: create company query.
@app.route('/api/finnish-companies', methods=['POST'])
@validate_request(FinnishCompanyQuery)  # For POST, validate_request goes after route decorator.
@validate_response(QueryResponse, 200)     # For POST, validate_response comes next.
async def create_company_query(data: FinnishCompanyQuery):
    # Validate that companyName is provided is already enforced by dataclass schema.
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat() + "Z"
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at, "results": None}
    
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, data.__dict__))
    
    return QueryResponse(queryId=job_id, status="processing", requestedAt=requested_at)


# GET endpoint: get query results. No request body validation needed.
@app.route('/api/results/<job_id>', methods=['GET'])
async def get_query_results(job_id: str):
    job = entity_jobs.get(job_id)
    if not job:
        abort(404, description="Query ID not found")
    return jsonify({
        "queryId": job_id,
        "status": job["status"],
        "requestedAt": job["requestedAt"],
        "results": job["results"]
    })


# Processing task: calls external APIs and aggregates results.
async def process_entity(job_id: str, data: dict):
    async with aiohttp.ClientSession() as session:
        finnish_api_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
        params = {"name": data.get("companyName")}
        if data.get("location"):
            params["location"] = data["location"]
        if data.get("registrationDateStart"):
            params["registrationDateStart"] = data["registrationDateStart"]
        if data.get("registrationDateEnd"):
            params["registrationDateEnd"] = data["registrationDateEnd"]
        # TODO: Add additional parameters based on requirements if available.
        try:
            async with session.get(finnish_api_url, params=params) as resp:
                if resp.status != 200:
                    entity_jobs[job_id]["status"] = "error"
                    entity_jobs[job_id]["results"] = {"error": "Failed to retrieve data from Finnish API"}
                    return
                finnish_data = await resp.json()
        except Exception as e:
            entity_jobs[job_id]["status"] = "error"
            entity_jobs[job_id]["results"] = {"error": str(e)}
            return

        # TODO: Adjust based on actual response content; assuming a 'results' list is provided.
        companies: List[Dict[str, Any]] = finnish_data.get("results", [])

        # Filter out inactive companies.
        active_companies = []
        for company in companies:
            # Assuming the company status field is named 'status'
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

        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["results"] = results
        entity_jobs[job_id]["completedAt"] = datetime.datetime.utcnow().isoformat() + "Z"


# External LEI enrichment using aiohttp.
async def fetch_and_enrich_lei(session: aiohttp.ClientSession, company: dict) -> dict:
    # TODO: Replace with a valid official LEI registry or reliable financial data source.
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