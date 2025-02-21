Below is an example prototype.py file that implements the design using Quart with aiohttp for asynchronous HTTP requests and an in-memory cache for job persistence. In this implementation, external calls are simulated with placeholders that include TODO comments where additional work or validation is required.

-------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
from datetime import datetime

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

app = Quart(__name__)
# Add QuartSchema (we use it without @validate_request because the input data is dynamic)
QuartSchema(app)

# In-memory storage for query jobs.
jobs = {}  # { job_id: { "status": "processing"/"done"/"failed", "requestedAt": ..., "results": [...] } }

# Async function to process company data: query the PRH API, filter, and enrich with LEI data.
async def process_entity(job_id, data):
    company_name = data.get("company_name")
    registration_date_start = data.get("registration_date_start")
    registration_date_end = data.get("registration_date_end")
    page = data.get("page", 1)
    
    # Build query parameters for the Finnish Companies Registry API.
    prh_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
    params = {"name": company_name, "page": page}
    if registration_date_start:
        params["registrationDateStart"] = registration_date_start
    if registration_date_end:
        params["registrationDateEnd"] = registration_date_end
    
    # Query the PRH Avoindata API.
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(prh_url, params=params) as resp:
                prh_data = await resp.json()
                # TODO: Adapt the parsing of prh_data based on the actual API response format.
        except Exception as e:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = f"Error fetching data from PRH: {str(e)}"
            return
    
    # For demonstration purposes, assume the response contains a key "results" listing companies.
    companies = prh_data.get("results", [])
    # If no companies were returned, create a dummy record for demo purposes.
    if not companies:
        companies = [{
            "company_name": "Demo Company",
            "business_id": "1234567-8",
            "company_type": "OY",
            "registration_date": "2020-01-01",
            "status": "Active"
        }]
    
    # Filter out companies that are not active.
    active_companies = [c for c in companies if c.get("status", "").lower() == "active"]
    
    enriched_results = []
    # Enrich each active company with LEI data.
    for company in active_companies:
        lei = await fetch_lei(company)
        # Add the LEI information to the company record.
        company["lei"] = lei if lei else "Not Available"
        enriched_results.append(company)
    
    # Save the enriched results in the in-memory cache.
    jobs[job_id]["results"] = enriched_results
    jobs[job_id]["status"] = "done"
    jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()

# Helper function that simulates fetching LEI details from an external service.
async def fetch_lei(company):
    # TODO: Replace with an actual call to a LEI provider API when available.
    async with aiohttp.ClientSession() as session:
        # Simulate a delay that might occur when calling an external service.
        await asyncio.sleep(1)
        business_id = company.get("business_id", "")
        # Dummy logic: return a fake LEI if the business_id ends with an even digit.
        if business_id and business_id[-1] in "02468":
            return "LEI-" + business_id
        else:
            return None

# Endpoint to initiate the query processing.
@app.route("/companies/query", methods=["POST"])
async def companies_query():
    data = await request.get_json()
    # TODO: Add more robust input validation if needed.
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    # Fire and forget the background processing task.
    asyncio.create_task(process_entity(job_id, data))
    return jsonify({"job_id": job_id, "status": "processing"})

# Endpoint to retrieve the result of a previously submitted query.
@app.route("/companies/result/<job_id>", methods=["GET"])
async def companies_result(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if job["status"] == "processing":
        return jsonify({"job_id": job_id, "status": "processing"})
    elif job["status"] == "failed":
        return jsonify({"job_id": job_id, "status": "failed", "error": job.get("error")}), 500
    else:
        return jsonify({
            "job_id": job_id,
            "status": "done",
            "results": job.get("results"),
            "metadata": {"completedAt": job.get("completedAt")}
        })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
-------------------------------------------------

Notes:
• This prototype uses an in-memory dictionary (jobs) to store query jobs and results.
• External API calls use aiohttp.ClientSession. Real endpoints should include robust error handling and data validation.
• The async processing (via asyncio.create_task) allows the POST endpoint to return a job_id immediately.
• Replace the TODO comments with actual validations and integration details as the specification evolves.

This working prototype should help verify the UX and expose any gaps for further refinement.