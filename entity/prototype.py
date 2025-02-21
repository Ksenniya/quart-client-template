Below is the updated prototype.py with validation decorators added. Note that for POST endpoints the order of decorators is as follows (route first, then validate_request, then validate_response) as a workaround for a known issue in quart-schema. For GET endpoints with parameters you must use the standard approach (accessing query params from request.args). Additional TODO comments mark mocks and placeholders.

------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from dataclasses import dataclass
from quart import Quart, jsonify, request, abort
from quart_schema import QuartSchema, validate_request, validate_response  # Also use validate_querystring if needed
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # single-line integration per requirements

# Dataclasses for validation
@dataclass
class CompanySearchRequest:
    companyName: str  # Required field, using only primitives

@dataclass
class JobResponse:
    jobId: str
    message: str

# In-memory store for job status and processed results
entity_jobs = {}

# Constants for external APIs
PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
# TODO: Provide actual URL or authentication details for the LEI lookup service.
LEI_API_BASE = "https://example.com/lei-lookup"  # Placeholder URL

async def fetch_companies(company_name: str) -> list:
    """Fetch companies from the Finnish Companies Registry API by company name."""
    params = {"name": company_name}
    async with aiohttp.ClientSession() as session:
        async with session.get(PRH_API_BASE, params=params) as resp:
            if resp.status != 200:
                # TODO: Improve error handling based on PRH API errors.
                return []
            data = await resp.json()
            # Assuming data format is similar to { "results": [ { company data }, ... ] }
            return data.get("results", [])  # Placeholder extraction

async def fetch_lei(company_info: dict) -> str:
    """Fetch LEI for a company using an external LEI lookup service."""
    # TODO: Replace this mock with a real API call.
    # For demonstration, assume if the length of companyName is even, an LEI is found.
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
    # TODO: Verify the actual key and values indicating active status.
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
            "status": "Active",  # We filtered out inactive companies already
            "lei": lei,
        }
        results.append(enriched)

    # 4. Save the processed results in our in-memory cache
    entity_jobs[job_id]["results"] = results
    entity_jobs[job_id]["status"] = "completed"

# POST endpoint: all external fetching, filtering, enrichment are done here.
# Workaround: For POST endpoints, the route decorator must be first,
# then validate_request and validate_response, as per quart-schema known issue.
@app.route("/api/companies/search", methods=["POST"])
@validate_request(CompanySearchRequest)  # This decorator must follow the route decorator.
@validate_response(JobResponse, 201)
async def search_companies(data: CompanySearchRequest):
    # The validated payload is received as 'data'
    # Create a unique job identifier and store initial job data in our in-memory cache.
    job_id = str(uuid.uuid4())
    entity_jobs[job_id] = {"status": "processing", "requestedAt": None, "results": None}

    # Fire and forget the processing task.
    # TODO: Consider logging or exception handling for background tasks.
    asyncio.create_task(process_entity(job_id, data.__dict__))

    # Return the job id so that client can poll for results.
    return jsonify({
        "jobId": job_id,
        "message": "Search initiated. Use jobId to poll for results."
    }), 201

# GET endpoint: used for retrieving results via job_id.
# Since GET requests do not contain a body, no validation decorators are needed.
@app.route("/api/companies/<job_id>", methods=["GET"])
async def get_search_results(job_id):
    job = entity_jobs.get(job_id)
    if not job:
        abort(404, description="Job not found")

    # If processing is still underway, indicate that.
    if job["status"] != "completed":
        return jsonify({
            "jobId": job_id,
            "status": job["status"],
            "message": "Processing. Please check back later."
        })

    # Return the completed results.
    return jsonify({
        "jobId": job_id,
        "completed": True,
        "results": job.get("results", [])
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
------------------------------------------

Notes:
• The dataclasses CompanySearchRequest and JobResponse are used for request and response validation.
• For POST endpoints, the order is: @app.route, then @validate_request, then @validate_response.
• GET endpoints access parameters via request.args (or path parameters), so no validation decorators are applied.
• TODO comments indicate areas where a more robust solution or real external API implementation is needed.
• This prototype uses an in-memory dictionary (entity_jobs) to mock persistence.