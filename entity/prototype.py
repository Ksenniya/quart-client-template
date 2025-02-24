Below is a prototype implementation in a file called prototype.py. In this example, all external calls are made using aiohttp.ClientSession. Business logic (data retrieval, filtering, LEI enrichment) is done in a POST endpoint, and a GET endpoint returns the cached results. Mocks and TODO comments have been added where external services or persistence details are still unclear.

---------------------------------------------------------------
#!/usr/bin/env python3
"""
prototype.py

A working prototype of the Finnish Companies Data Retrieval and Enrichment Application.
Uses Quart and QuartSchema for API endpoints and aiohttp for external HTTP requests.
Persistence is mocked with an in-memory dictionary.
"""

import asyncio
import uuid
import datetime
from quart import Quart, request, jsonify
from quart_schema import QuartSchema  # Single-line integration with QuartSchema
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Local in-memory cache to simulate persistence for job results.
jobs = {}  # Example structure: jobs[job_id] = {"status": "processing", "requestedAt": ..., "results": ...}

# -------------------------------
# Helper Functions and Business Logic
# -------------------------------

async def fetch_company_data(params):
    """
    Call the Finnish Companies Registry API to fetch company information.
    Uses the "name" query parameter from our input.
    """
    url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
    # Construct query parameters based on available input.
    # TODO: Add more parameters if needed.
    query_params = {"name": params.get("companyName")}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=query_params) as resp:
            if resp.status == 200:
                data = await resp.json()
                # TODO: Validate that the structure of 'data' meets our requirements.
                return data
            else:
                # TODO: Improve error handling for external API failures.
                return {"results": []}

async def fetch_lei_for_company(company):
    """
    Fetch the Legal Entity Identifier (LEI) for a given company.
    For this prototype, we use a mock implementation.
    """
    # TODO: Replace this placeholder with an actual call to a reliable LEI registry.
    await asyncio.sleep(0.1)  # Simulate network latency.
    # For demonstration, return a dummy LEI if the company name length is even, else "Not Available".
    if len(company.get("name", "")) % 2 == 0:
        return "529900T8BM49AURSDO55"
    else:
        return "Not Available"

async def process_entity(job_id, data):
    """
    Process the request: retrieve company info, filter active companies, enrich with LEI info.
    """
    try:
        # 1. Fetch companies from the Finnish Companies Registry API.
        external_data = await fetch_company_data(data)
        companies = external_data.get("results", [])
        
        # 2. Filter out inactive companies.
        # TODO: Update filtering logic based on actual external data fields (e.g., check 'status' or other indicators).
        active_companies = [c for c in companies if str(c.get("status", "")).lower() == "active"]
        
        # 3. For each active company, retrieve LEI data.
        results = []
        for company in active_companies:
            company_info = {
                "companyName": company.get("name"),            # Assuming external API defines company name as "name"
                "businessId": company.get("businessId"),         # Assuming key is "businessId"
                "companyType": company.get("companyForm"),       # Assuming key is "companyForm"
                "registrationDate": company.get("registrationDate"),  # TODO: Confirm field name from external API.
                "status": "Active"
            }
            lei = await fetch_lei_for_company(company)
            company_info["LEI"] = lei
            results.append(company_info)
        
        # 4. Update the job status with results.
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["results"] = results
    except Exception as e:
        # In case of an error, mark the job as 'failed'.
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)

# -------------------------------
# API Endpoints
# -------------------------------

@app.route('/api/companies/enrich', methods=['POST'])
async def enrich_companies():
    """
    POST endpoint for processing company search and enrichment.
    This endpoint accepts search parameters, triggers processing, and
    returns a job id for async result retrieval.
    """
    data = await request.get_json()
    if not data or "companyName" not in data:
        return jsonify({"error": "Missing required field: companyName"}), 400

    # Create a unique job id and store initial job data.
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.datetime.utcnow().isoformat()
    }
    
    # Fire and forget the processing task.
    # This pattern ensures the endpoint returns immediately while processing continues in the background.
    asyncio.create_task(process_entity(job_id, data))
    
    return jsonify({"job_id": job_id})

@app.route('/api/companies/results', methods=['GET'])
async def get_results():
    """
    GET endpoint for retrieving results of a previously requested job.
    The client should supply the job id as a query parameter.
    """
    job_id = request.args.get("job_id")
    if not job_id or job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(jobs[job_id])

# -------------------------------
# Entry Point
# -------------------------------

if __name__ == '__main__':
    # Run the application with specified settings.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

---------------------------------------------------------------
Notes:
• The external API calls (Finnish Companies Registry API and LEI lookup) use mocks where the actual field names or endpoints may differ.
• The filtering for active companies currently expects a field "status" in the external API’s response. Adjust this as needed.
• Persistence is kept in-memory in the variable 'jobs' for prototype/demo purposes.

This prototype should allow you to verify the UX and identify any gaps in requirements before proceeding with a complete implementation.