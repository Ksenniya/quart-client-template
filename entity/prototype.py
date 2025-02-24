Below is the prototype.py file that implements the API design. This prototype uses Quart with QuartSchema (without request validation), aiohttp.ClientSession for external HTTP calls, and a simple in‑memory dictionary (entity_jobs) for caching jobs. In places where a real external API or persistent storage would be used, TODO comments have been added.

--------------------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
from datetime import datetime

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema  # Integrates schema support without validations

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Local in-memory cache for job persistence (mock persistence)
entity_jobs = {}  # Example: entity_jobs[job_id] = {"status": "processing", "requestedAt": "...", "results": [...]}

async def process_entity(job_id, input_data):
    """
    Process the data enrichment in background:
      • Calls the Finnish Companies Registry API.
      • Filters out inactive companies.
      • Enriches active companies with LEI data from an external API.
    """
    job = entity_jobs[job_id]
    company_name = input_data.get("companyName")
    filters = input_data.get("filters", {})

    # Step 1: Retrieve company data from the Finnish Companies Registry API
    async with aiohttp.ClientSession() as session:
        prh_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
        # Prepare query parameters: companyName and any additional filters.
        params = {"name": company_name}
        params.update(filters)  # TODO: Map additional filters to actual API query parameters if necessary.
        try:
            async with session.get(prh_url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Assuming data contains a "results" field with the companies list.
                    companies = data.get("results", [])
                else:
                    companies = []
        except Exception as e:
            print(f"Error calling PRH API: {e}")
            companies = []

    # For prototype purposes, if no companies are returned, simulate dummy data.
    if not companies:
        companies = [
            {
                "Company Name": company_name,
                "Business ID": "1234567-8",
                "Company Type": "OY",
                "Registration Date": "2020-01-01",
                "Status": "Active"
            },
            {
                "Company Name": f"{company_name} Inactive",
                "Business ID": "8765432-1",
                "Company Type": "OY",
                "Registration Date": "2019-01-01",
                "Status": "Inactive"
            }
        ]

    # Step 2: Filter out inactive companies (active companies have Status == "Active")
    active_companies = [company for company in companies if company.get("Status") == "Active"]

    # Step 3: Enrich each active company with LEI data
    for company in active_companies:
        async with aiohttp.ClientSession() as session:
            lei_api_url = "https://example.com/lei"  # TODO: Replace with the real external LEI API endpoint.
            # Mock request payload - here we use Business ID to search for the LEI.
            payload = {"businessId": company["Business ID"]}
            try:
                async with session.post(lei_api_url, json=payload) as resp:
                    if resp.status == 200:
                        lei_data = await resp.json()
                        company["LEI"] = lei_data.get("LEI", "Not Available")
                    else:
                        company["LEI"] = "Not Available"
            except Exception as e:
                print(f"Error calling LEI API: {e}")
                company["LEI"] = "Not Available"
        # For the prototype, if no LEI was provided, assign a dummy LEI code.
        if not company.get("LEI"):
            company["LEI"] = "LEI1234567890"  # TODO: Replace with actual logic in production.

    # Step 4: Update the job status with the enriched results.
    job["results"] = active_companies
    job["status"] = "completed"
    job["completedAt"] = datetime.utcnow().isoformat()

@app.route('/companies/enrich', methods=['POST'])
async def enrich_companies():
    """
    POST endpoint to trigger external data retrieval and enrichment.
    External API calls (Finnish Companies Registry API and LEI API) occur in this task.
    """
    input_data = await request.get_json()
    # Validate required field
    if not input_data or "companyName" not in input_data:
        return jsonify({"error": "companyName is required"}), 400

    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()
    # Initialize the job in our local cache
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at, "results": None}

    # Fire and forget the background task (processing the entity)
    asyncio.create_task(process_entity(job_id, input_data))

    return jsonify({
        "taskId": job_id,
        "message": "Data retrieval and enrichment in progress or completed."
    }), 201

@app.route('/companies/results/<job_id>', methods=['GET'])
async def get_results(job_id):
    """
    GET endpoint for retrieving enriched company data by task/job id.
    """
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Task ID not found"}), 404

    return jsonify({
        "taskId": job_id,
        "status": job["status"],
        "requestedAt": job["requestedAt"],
        "completedAt": job.get("completedAt"),
        "results": job["results"]
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

--------------------------------------------------------------

This prototype code should help verify the user experience (UX) and expose any gaps in the requirements. Areas using mocks or simplified logic are marked with TODO comments for future enhancement.