Below is an example prototype.py file. This code uses Quart for the async web framework and aiohttp for external HTTP calls. External API calls to the Finnish Companies Registry and LEI data source are implemented in the POST endpoint. A simple in‑memory dictionary (jobs) is used to mimic a persistent cache. Mocks and TODO comments are included where details are unclear.

--------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from quart import Quart, request, jsonify
import aiohttp

app = Quart(__name__)
# Add QuartSchema support (data is dynamic so we are not using input validators yet)
from quart_schema import QuartSchema
QuartSchema(app)

# Simple in-memory persistence for job data.
jobs = {}  # Example: jobs[job_id] = {"status": "processing", "requestedAt": ..., "results": [...]}

# External API call to Finnish Companies Registry API.
async def fetch_company_data(company_name, filters):
    url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
    # Build query parameters using company_name and any provided filters.
    params = {'name': company_name}
    if filters:
        params.update(filters)
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data
            else:
                # TODO: Specify more robust error handling
                return {"results": []}

# External API call to retrieve LEI information.
async def fetch_lei_for_company(business_id):
    # TODO: Replace with actual LEI data source integration.
    # Here we use a simple mock: if the business_id ends with an even digit, use a dummy LEI.
    await asyncio.sleep(0.1)  # simulate network delay
    if business_id and business_id[-1] in "02468":
        return "529900T8BM49AURSDO55"
    else:
        return "Not Available"

# Background task that performs data retrieval and enrichment.
async def process_entity(job_id, data):
    company_name = data.get("companyName")
    filters = data.get("filters", {})
    # Retrieve companies data from the Finnish Companies Registry.
    company_data = await fetch_company_data(company_name, filters)
    
    # Filtering: here, we assume each company record contains a key "status" to indicate active status.
    results = company_data.get("results", [])
    active_companies = []
    for company in results:
        # TODO: Adjust this check based on the actual API response structure.
        # Assume a company without a status or with status "active" should be kept.
        status_field = company.get("status", "").lower()
        if status_field == "active" or status_field == "":
            active_companies.append(company)
    
    enriched_results = []
    for company in active_companies:
        # Extract required fields; using defaults if they are not available.
        name = company.get("name", "Unknown")
        business_id = company.get("businessId", "Unknown")
        company_type = company.get("companyForm", "Unknown")
        registration_date = company.get("registrationDate", "Unknown")
        status = "Active"
        # Enrich data with LEI information.
        lei = await fetch_lei_for_company(business_id)
        enriched_results.append({
            "companyName": name,
            "businessId": business_id,
            "companyType": company_type,
            "registrationDate": registration_date,
            "status": status,
            "lei": lei
        })
    
    # Update the job entry in the cache with the final results.
    jobs[job_id]["status"] = "completed"
    jobs[job_id]["results"] = enriched_results

# POST endpoint to initiate the search and data enrichment process.
@app.route('/companies/search', methods=['POST'])
async def search_companies():
    data = await request.get_json()
    if not data or "companyName" not in data:
        return jsonify({"error": "companyName is required"}), 400

    # Generate a job id and record the request.
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()
    jobs[job_id] = {"status": "processing", "requestedAt": requested_at}
    # Fire and forget the background task.
    asyncio.create_task(process_entity(job_id, data))
    
    # Return a preliminary response with the job id.
    return jsonify({
        "requestId": job_id,
        "status": "processing",
        "message": "Your request is being processed. Use the GET endpoint with your requestId to retrieve the results."
    })

# GET endpoint to retrieve the results of the search using the job id.
@app.route('/companies/search/<job_id>', methods=['GET'])
async def get_search_results(job_id):
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(jobs[job_id])

# Entry point for the application.
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

--------------------------------------------------

Below is a Mermaid sequence diagram outlining the user-app interaction:

--------------------------------------------------
sequenceDiagram
    participant U as User
    participant A as Application Server
    participant F as Finnish Companies Registry API
    participant L as LEI Data Source

    U->>A: POST /companies/search {companyName, filters}
    A->>F: Request companies data using companyName & filters
    F-->>A: Returns companies data
    A->>A: Filter out inactive companies
    loop For each active company
      A->>L: Request LEI based on businessId
      L-->>A: Returns LEI or "Not Available"
    end
    A->>A: Compile and store enriched results with jobId
    A-->>U: Returns jobId and processing status
    U->>A: GET /companies/search/{jobId}
    A-->>U: Returns processed results (or processing status)

--------------------------------------------------

This prototype verifies the UX and end-to-end flow while highlighting where further details are needed using TODOs for future refinement before a production-ready implementation.