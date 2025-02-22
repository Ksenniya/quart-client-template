Below is the updated prototype.py code. In this version, we add validations using the quart‑schema decorators. For POST endpoints, note that we intentionally place the route decorator at the top and validation decorators afterward (a workaround for an issue in the quart‑schema library). For GET endpoints with query parameters, the validation decorator is placed first as recommended, but our GET endpoint here does not require querystring validation.

------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
from datetime import datetime
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response  # note: for GET endpoints with querystring, use validate_querystring as needed.
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# In-memory cache for job persistence (mock persistence)
entity_jobs = {}

# Constants for external APIs
PRH_API_URL = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
# TODO: Replace with the actual LEI lookup API endpoint if available.
LEI_API_URL = "https://example.com/lei-lookup"  

# -------------------------------------------------------------------------
# Data models for validation. Only primitives are used.
# -------------------------------------------------------------------------
@dataclass
class EnrichRequest:
    companyName: str
    outputFormat: str = "json"  # Optional; default is JSON.

@dataclass
class EnrichResponse:
    jobId: str
    message: str

# -------------------------------------------------------------------------
# External Calls (with mocks and TODOs)
# -------------------------------------------------------------------------
async def fetch_company_data(session: aiohttp.ClientSession, company_name: str):
    """
    Query the Finnish Companies Registry API using the company name.
    Invoked internally via the POST endpoint.
    """
    params = {"name": company_name}
    async with session.get(PRH_API_URL, params=params) as resp:
        if resp.status == 200:
            data = await resp.json()
            # TODO: Adapt to the actual structure of the API response.
            return data.get("results", [])
        else:
            # TODO: Add more robust error handling.
            return []

async def lookup_lei(session: aiohttp.ClientSession, company):
    """
    Lookup the Legal Entity Identifier (LEI) for the company.
    This is currently a placeholder.
    """
    await asyncio.sleep(0.1)  # Simulated network latency.
    # TODO: Replace with an actual call to an LEI lookup service.
    if len(company.get("companyName", "")) % 2 == 0:
        return "5493001KJTIIGC8Y1R12"
    else:
        return "Not Available"

# -------------------------------------------------------------------------
# Background Processing Task
# -------------------------------------------------------------------------
async def process_entity(job_id: str, input_data: dict):
    """
    Background task to retrieve and enrich company data.
    Updates the in-memory job cache once done.
    """
    entity_jobs[job_id]["status"] = "processing"
    company_name = input_data.get("companyName")
    
    async with aiohttp.ClientSession() as session:
        companies = await fetch_company_data(session, company_name)
        
        # TODO: Determine the proper fields from the PRH API response.
        active_companies = []
        for comp in companies:
            # Here, we assume that a company is active if comp["status"] equals "active" (case-insensitive).
            if comp.get("status", "").lower() == "active":
                active_companies.append(comp)
        
        enriched_companies = []
        for comp in active_companies:
            lei_val = await lookup_lei(session, comp)
            enriched_companies.append({
                "companyName": comp.get("companyName", "Unknown"),  # TODO: Adjust field if different.
                "businessId": comp.get("businessId", "Unknown"),
                "companyType": comp.get("companyType", "Unknown"),
                "registrationDate": comp.get("registrationDate", "Unknown"),
                "status": "Active",
                "LEI": lei_val,
            })
        
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["results"] = enriched_companies
        entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()

# -------------------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------------------
# POST /companies/enrich
# Note: For POST endpoints, route decorator goes first, then validation decorators.
# This ordering is a workaround for an issue with quart-schema.
@app.route("/companies/enrich", methods=["POST"])
@validate_request(EnrichRequest)
@validate_response(EnrichResponse, 202)
async def enrich_companies(data: EnrichRequest):
    """
    Accepts a company name and initiates the enrichment process.
    The external API calls and enrichment are handled in a background task.
    """
    # Create a unique job_id to track the enrichment process.
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()
    entity_jobs[job_id] = {"status": "queued", "requestedAt": requested_at, "results": None}
    
    # Fire and forget: process_entity is executed asynchronously.
    asyncio.create_task(process_entity(job_id, data.__dict__))
    
    return jsonify({
        "jobId": job_id,
        "message": "Enrichment processing started. Use the jobId to retrieve results."
    }), 202

# GET /companies/results/<job_id>
# No request body or querystring is expected; therefore, no validation is added.
@app.route("/companies/results/<job_id>", methods=["GET"])
async def get_results(job_id: str):
    """
    Retrieves the enriched data for a given job id.
    """
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    if job["status"] != "completed":
        return jsonify({
            "jobId": job_id,
            "status": job["status"],
            "message": "Results are not ready yet."
        }), 202

    return jsonify({
        "jobId": job_id,
        "results": job.get("results", [])
    }), 200

if __name__ == '__main__':
    # Using threaded=True to allow background async tasks to run in this prototype.
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
------------------------------------------------

This prototype now uses validate_request and validate_response in the POST endpoint as per the approved design, with additional comments explaining the decorator ordering workaround. Further details (e.g., actual API responses, advanced error handling, and integration of LEI lookup) remain as TODO items for future iterations.