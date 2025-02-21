Below is a working prototype for your project. This implementation uses Quart with QuartSchema (adding it as one line) and aiohttp.ClientSession for HTTP requests. Mocks and TODO comments are provided where external data or persistence details are uncertain:

------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from quart import Quart, request, jsonify
from quart_schema import QuartSchema  # One-liner initializing the schema

import aiohttp

app = Quart(__name__)
QuartSchema(app)

# In-memory cache to simulate persistence
entity_jobs = {}

# Async function to simulate processing a search request:
async def process_entity(job_id, criteria):
    try:
        # Create an aiohttp ClientSession for external API calls
        async with aiohttp.ClientSession() as session:
            prh_api_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
            params = {"name": criteria.get("name"), "page": criteria.get("page", 1)}
            async with session.get(prh_api_url, params=params) as resp:
                if resp.status != 200:
                    # TODO: Handle non-200 responses properly in production.
                    prh_data = {"results": []}  # Using empty placeholder data
                else:
                    prh_data = await resp.json()
            
            # TODO: Adapt below parsing based on actual PRH API response structure.
            # Filter the companies for active status.
            active_companies = []
            for company in prh_data.get("results", []):
                # Assuming each company has a 'status' field marked "Active" or "Inactive".
                if company.get("status", "").lower() == "active":
                    active_companies.append(company)
            
            # Enrich active companies with LEI data.
            enriched_results = []
            # NOTE: Using same ClientSession for simulation; you might use a dedicated one in production.
            for company in active_companies:
                lei = await fetch_lei_for_company(company, session)
                enriched_company = {
                    "companyName": company.get("name", "N/A"),  # Adjust mapping as needed.
                    "businessId": company.get("businessId", "N/A"),
                    "companyType": company.get("companyType", "N/A"),
                    "registrationDate": company.get("registrationDate", "N/A"),
                    "status": company.get("status", "N/A"),
                    "LEI": lei,
                }
                enriched_results.append(enriched_company)
        
        # Update our in-memory cache with the finished result.
        entity_jobs[job_id]["results"] = enriched_results
        entity_jobs[job_id]["completed"] = True
        entity_jobs[job_id]["status"] = "completed"
    except Exception as e:
        # In case of processing error, update job status to failed.
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)

# Async function to fetch LEI for a company.
async def fetch_lei_for_company(company, session):
    # TODO: Replace this mock with a call to an official LEI API or reliable financial data source.
    await asyncio.sleep(0.1)  # Simulate network call delay.
    return "Not Available"  # Placeholder value if LEI is not found.

# POST endpoint to initiate a search/search processing.
@app.route('/api/v1/companies/search', methods=['POST'])
async def search_companies():
    data = await request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "Company name is required"}), 400

    # Generate a unique request ID.
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()

    # Store initial job details in the in-memory cache.
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": requested_at
    }

    # Fire-and-forget the external data processing.
    asyncio.create_task(process_entity(job_id, data))
    return jsonify({
        "requestId": job_id,
        "status": "processing",
        "message": "Search initiated. Please poll the GET endpoint for results."
    })

# GET endpoint to retrieve the results by requestId.
@app.route('/api/v1/companies/results', methods=['GET'])
async def get_results():
    job_id = request.args.get("requestId")
    if not job_id:
        return jsonify({"error": "requestId parameter is required"}), 400

    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify({
        "requestId": job_id,
        "results": job.get("results", []),
        "completed": job.get("completed", False),
        "status": job.get("status")
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
------------------------------------------------

This prototype adheres to the API design by:

• Performing external API calls and LEI enrichment within the POST endpoint.
• Storing the results in a local in-memory cache (entity_jobs).
• Allowing the client to poll the GET endpoint using the unique requestId.

Each mock or placeholder section is marked with a TODO comment, to remind us to refine the implementation when the requirements are more fully defined.