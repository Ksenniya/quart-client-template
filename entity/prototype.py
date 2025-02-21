Below is the revised prototype with request validation added. Note that we define two dataclasses—one for the POST request body and one for the GET query string—and we add the decorators in the proper order. For POST endpoints, route comes first, then validate_request then validate_response; for GET endpoints, we place validate_querystring before the route. (This decorator order is a workaround to an issue in the quart-schema library.) 

------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring  # Import decorators
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # One-line schema initialization

# In-memory cache to simulate persistence.
entity_jobs = {}

# -----------------------------
# Dataclasses for request validation
# -----------------------------
@dataclass
class CompanySearchReq:
    name: str
    page: int = 1

@dataclass
class JobQuery:
    requestId: str

# -----------------------------
# Async function to process the external API calls and enrichment.
# -----------------------------
async def process_entity(job_id, criteria: CompanySearchReq):
    try:
        # Create an aiohttp ClientSession for external API calls.
        async with aiohttp.ClientSession() as session:
            prh_api_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
            params = {"name": criteria.name, "page": criteria.page}
            async with session.get(prh_api_url, params=params) as resp:
                if resp.status != 200:
                    # TODO: Handle non-200 responses properly in production.
                    prh_data = {"results": []}  # Placeholder data when error occurs.
                else:
                    prh_data = await resp.json()

            # TODO: Adapt parsing below based on the actual PRH API response structure.
            # Filter companies for "active" status.
            active_companies = []
            for company in prh_data.get("results", []):
                # Assuming each company has a 'status' field with "Active" or "Inactive".
                if company.get("status", "").lower() == "active":
                    active_companies.append(company)

            # Enrich each active company with LEI data.
            enriched_results = []
            for company in active_companies:
                lei = await fetch_lei_for_company(company, session)
                enriched_company = {
                    "companyName": company.get("name", "N/A"),     # Adjust mapping as needed.
                    "businessId": company.get("businessId", "N/A"),
                    "companyType": company.get("companyType", "N/A"),
                    "registrationDate": company.get("registrationDate", "N/A"),
                    "status": company.get("status", "N/A"),
                    "LEI": lei,
                }
                enriched_results.append(enriched_company)

        # Update in-memory cache with the finished result.
        entity_jobs[job_id]["results"] = enriched_results
        entity_jobs[job_id]["completed"] = True
        entity_jobs[job_id]["status"] = "completed"
    except Exception as e:
        # In case of processing error, update job status to failed.
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)

# -----------------------------
# Async function to fetch LEI data (mock implementation).
# -----------------------------
async def fetch_lei_for_company(company, session):
    # TODO: Replace this mock with a call to an official LEI API or a reliable financial data source.
    await asyncio.sleep(0.1)  # Simulate network call delay.
    return "Not Available"  # Placeholder value if LEI is not found.

# -----------------------------
# POST endpoint to initiate company search and enrichment.
# Decorators order for POST: route first, then validate_request, then validate_response.
# -----------------------------
@app.route('/api/v1/companies/search', methods=['POST'])
@validate_request(CompanySearchReq)  # This should be the second line in POST endpoints.
@validate_response(dict, 200)          # Using dict as response type for now.
async def search_companies(data: CompanySearchReq):
    # Data validated by quart_schema.
    if not data.name:
        return jsonify({"error": "Company name is required"}), 400

    # Generate a unique request ID.
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()

    # Store initial job details in local in-memory cache.
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": requested_at
    }

    # Fire-and-forget the external processing task.
    asyncio.create_task(process_entity(job_id, data))
    return jsonify({
        "requestId": job_id,
        "status": "processing",
        "message": "Search initiated. Please poll the GET endpoint for results."
    })

# -----------------------------
# GET endpoint to retrieve the search results.
# Decorators order for GET: validation decorator first, then route.
# This is a known workaround for GET requests as described in quart-schema examples.
# -----------------------------
@validate_querystring(JobQuery)  # This line MUST go first for GET request validation.
@app.route('/api/v1/companies/results', methods=['GET'])
async def get_results():
    # Note: Do not accept parameters in the function signature for GET requests.
    requestId = request.args.get("requestId")
    if not requestId:
        return jsonify({"error": "requestId parameter is required"}), 400

    job = entity_jobs.get(requestId)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify({
        "requestId": requestId,
        "results": job.get("results", []),
        "completed": job.get("completed", False),
        "status": job.get("status")
    })

# -----------------------------
# Application entry point
# -----------------------------
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
------------------------------------------------

This prototype now:
• Uses quart-schema decorators for request and response validation.
• Follows the required decorator order workaround (GET: validate_querystring first, POST: route then validate_request then validate_response).
• Mocks external API calls (PRH and LEI retrieval) and persistence using an in-memory cache.
• Contains TODO comments where further production detail is needed.

This should help verify the user experience and uncover any missing requirements before further implementation.