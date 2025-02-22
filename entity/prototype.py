Below is an example prototype.py that follows your instructions. Note that external calls for the Finnish Companies API and the LEI lookup are implemented via aiohttp, but they currently use mocks or placeholder logic with TODO comments. This prototype uses a local in‐memory dictionary (entity_jobs) for persistence.

------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
import json
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # Enable QuartSchema

# In-memory storage for job results
entity_jobs = {}

# Endpoint: POST /api/finnish-companies
@app.route('/api/finnish-companies', methods=['POST'])
async def create_company_query():
    data = await request.get_json()
    if not data or 'companyName' not in data:
        # For now, require at least a companyName
        abort(400, description="`companyName` is required")
    
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat() + "Z"
    # Initialize job record in our local cache
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at, "results": None}
    
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, data))
    
    return jsonify({"queryId": job_id, "status": "processing", "requestedAt": requested_at})

# Endpoint: GET /api/results/<job_id>
@app.route('/api/results/<job_id>', methods=['GET'])
async def get_query_results(job_id: str):
    job = entity_jobs.get(job_id)
    if not job:
        abort(404, description="Query ID not found")
    return jsonify({"queryId": job_id, "status": job["status"], "requestedAt": job["requestedAt"], "results": job["results"]})

# Processing task: calls external APIs and aggregates results.
async def process_entity(job_id: str, data: dict):
    # Create a session for external HTTP requests
    async with aiohttp.ClientSession() as session:
        # Step 1: Query Finnish Companies Registry API
        finnish_api_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
        params = {"name": data.get("companyName")}
        # Optionally add extra filters if provided in request
        if "location" in data:
            params["location"] = data["location"]
        if "registrationDateStart" in data:
            params["registrationDateStart"] = data["registrationDateStart"]
        if "registrationDateEnd" in data:
            params["registrationDateEnd"] = data["registrationDateEnd"]
        # TODO: Add additional parameters based on requirements, if available
        
        try:
            async with session.get(finnish_api_url, params=params) as resp:
                # TODO: adjust error handling based on actual API contract
                if resp.status != 200:
                    # Log error and update job status
                    entity_jobs[job_id]["status"] = "error"
                    entity_jobs[job_id]["results"] = {"error": "Failed to retrieve data from Finnish API"}
                    return
                finnish_data = await resp.json()
        except Exception as e:
            entity_jobs[job_id]["status"] = "error"
            entity_jobs[job_id]["results"] = {"error": str(e)}
            return
        
        # For the purpose of this prototype, assume finnish_data has a 'results' list
        companies = finnish_data.get("results", [])
        
        # Step 2: Filter out inactive companies.
        active_companies = []
        for company in companies:
            # Assuming the company status field is named 'status'
            if company.get("status", "").lower() == "active":
                active_companies.append(company)
        
        # Step 3: Enrich with LEI information.
        # For each active company, issue a call to an external LEI service
        tasks = []
        for company in active_companies:
            tasks.append(fetch_and_enrich_lei(session, company))
        enriched_companies = await asyncio.gather(*tasks)
        
        # Format the final result – include required fields
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
        
        # Update the job record in our local cache
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["results"] = results
        entity_jobs[job_id]["completedAt"] = datetime.datetime.utcnow().isoformat() + "Z"

# External LEI data enrichment using aiohttp.
async def fetch_and_enrich_lei(session: aiohttp.ClientSession, company: dict) -> dict:
    # TODO: Replace the URL with a valid, official LEI registry or reliable financial data source.
    lei_api_url = "http://example.com/lei"   # Placeholder URL
    params = {"businessId": company.get("businessId")}
    try:
        async with session.get(lei_api_url, params=params) as resp:
            # TODO: Handle response format for the LEI API
            if resp.status == 200:
                lei_data = await resp.json()
                # Assume lei_data contains field 'LEI'
                company["LEI"] = lei_data.get("LEI", "Not Available")
            else:
                company["LEI"] = "Not Available"
    except Exception as e:
        # Log exception in real implementation
        company["LEI"] = "Not Available"
    return company

if __name__ == '__main__':
    # Use the specified entry point for the prototype.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

------------------------------------------------

A few notes:  
• In the POST endpoint the processing is delegated via asyncio.create_task to simulate asynchronous, non-blocking processing.  
• The Finnish Companies API and LEI lookup are implemented with placeholder logic – TODO comments indicate where real API endpoints, error handling, or mapping of response formats should occur.  
• Data from the Finnish API is assumed to be contained in a 'results' list; adjust as needed once the API contract is finalized.

This prototype should help verify the UX and show potential gaps to be addressed in a more complete implementation.