Below is a working prototype (prototype.py) using Quart, aiohttp, and an in-memory cache. This version uses mocks (with corresponding TODO comments) for external API calls and persistence, and initiates asynchronous processing via asyncio.create_task.

------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from quart import Quart, jsonify, request, abort
from quart_schema import QuartSchema  # Include QuartSchema(app) as required
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # Single-line integration per requirements

# In-memory store for job status and processed results
entity_jobs = {}

# Constants for external APIs
PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
# TODO: Provide actual URL or API key for the LEI lookup service.
LEI_API_BASE = "https://example.com/lei-lookup"  # Placeholder URL

async def fetch_companies(company_name: str) -> list:
    """Fetch companies from the Finnish Companies Registry API by company name."""
    params = {"name": company_name}
    async with aiohttp.ClientSession() as session:
        async with session.get(PRH_API_BASE, params=params) as resp:
            if resp.status != 200:
                # TODO: Enhance error handling
                return []
            data = await resp.json()
            # Assuming data format is { "results": [ { company data }, ... ] }
            return data.get("results", [])  # Placeholder extraction

async def fetch_lei(company_info: dict) -> str:
    """Fetch LEI for a company using an external LEI lookup service."""
    # TODO: Replace this with a real API call if available. Currently a mock.
    # For demonstration, assume that if company name length is even, we find an LEI.
    if len(company_info.get("companyName", "")) % 2 == 0:
        return "MOCK-LEI-1234567890"
    return "Not Available"

async def process_entity(job_id: str, search_payload: dict):
    """Process the company search: fetch companies, filter and enrich with LEI."""
    # Record start time for job processing
    entity_jobs[job_id]["requestedAt"] = datetime.datetime.utcnow().isoformat()
    
    # 1. Fetch companies from PRH API
    company_name = search_payload.get("companyName", "")
    companies = await fetch_companies(company_name)

    # 2. Filter out inactive companies.
    # TODO: Check the actual key for business status. Using "status" and value "Active" as placeholder.
    active_companies = [
        company for company in companies
        if company.get("status", "").lower() == "active"
    ]
    
    # 3. For each active company, lookup the LEI.
    results = []
    for company in active_companies:
        lei = await fetch_lei(company)
        enriched = {
            "companyName": company.get("companyName", "N/A"),
            "businessId": company.get("businessId", "N/A"),
            "companyType": company.get("companyType", "N/A"),
            "registrationDate": company.get("registrationDate", "N/A"),
            "status": "Active",  # Since we filtered inactive companies out
            "lei": lei,
        }
        results.append(enriched)

    # 4. Save the processed results in our in-memory cache
    entity_jobs[job_id]["results"] = results
    entity_jobs[job_id]["status"] = "completed"
    
@app.route("/api/companies/search", methods=["POST"])
async def search_companies():
    data = await request.get_json()
    if not data or "companyName" not in data:
        abort(400, description="Missing required field: companyName")
    
    # Create a unique job identifier and store initial job data
    job_id = str(uuid.uuid4())
    entity_jobs[job_id] = {"status": "processing", "requestedAt": None, "results": None}
    
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, data))
    
    # Return the job id so that client can poll for results.
    return jsonify({
        "jobId": job_id,
        "message": "Search initiated. Use jobId to poll for results."
    })

@app.route("/api/companies/<job_id>", methods=["GET"])
async def get_search_results(job_id):
    job = entity_jobs.get(job_id)
    if not job:
        abort(404, description="Job not found")
    
    # If processing is still underway, indicate that
    if job["status"] != "completed":
        return jsonify({
            "jobId": job_id,
            "status": job["status"],
            "message": "Processing. Please check back later."
        })
    
    # Return the completed results
    return jsonify({
        "jobId": job_id,
        "completed": True,
        "results": job.get("results", [])
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
------------------------------------------------

Comments on the prototype:
• The external APIs (Finnish Companies Registry and LEI lookup) are invoked in asynchronous functions. Both use aiohttp.ClientSession.
• The persistence is mocked using the entity_jobs dictionary. 
• Each time a POST is received, a new job is created, then processed in the background.
• TODO comments indicate where additional implementation details (error handling, actual LEI lookup, etc.) are required.
• This prototype is intended to verify the UX and highlight any gaps before a full implementation.