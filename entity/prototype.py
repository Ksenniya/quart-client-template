Below is a working prototype implementation. This implementation uses aiohttp.ClientSession for external API calls, stores job results in an in‑memory dictionary, and dispatches background work via asyncio.create_task. Mocks and placeholders are marked with TODO comments where additional details are needed.

------------------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
import logging
import aiohttp

from quart import Quart, request, jsonify
from quart_schema import QuartSchema  # This adds schema support as required

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for job results
entity_jobs = {}

# Constants for external API endpoints
PRH_API_URL = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
# TODO: Replace with an actual LEI API endpoint or use multiple sources if available.
LEI_API_URL = "https://example.com/lei"  # Placeholder for LEI data source

async def fetch_lei_for_company(session: aiohttp.ClientSession, company: dict) -> str:
    # Placeholder implementation for LEI enrichment
    # TODO: Implement real logic to call official LEI registries or reliable sources.
    await asyncio.sleep(0.1)  # simulate network latency
    # For demo purposes, return a mock LEI. In a real scenario, conditionally set based on lookup success.
    return "LEI1234567890" if company.get("businessId") else "Not Available"

async def process_entity(job: dict, data: dict):
    logging.info("Starting processing for job %s", job["job_id"])
    try:
        # Create a client session for external HTTP calls
        async with aiohttp.ClientSession() as session:
            # Build the query parameters from the input data. Use only known keys.
            params = {}
            if "companyName" in data:
                params["name"] = data["companyName"]
            # TODO: Add additional filters from data if provided, such as registrationDateStart/End or companyForm.

            # Call the external Finnish Companies Registry API.
            async with session.get(PRH_API_URL, params=params) as resp:
                if resp.status != 200:
                    # Mark job as failed if call fails.
                    job["status"] = "failed"
                    job["error"] = f"Failed retrieving data from PRH API, status code {resp.status}"
                    return
                prh_data = await resp.json()

            # TODO: The structure of prh_data is assumed. Adapt filtering according to actual API response.
            companies = prh_data.get("results") or []
            # Filter out inactive companies.
            active_companies = [comp for comp in companies if comp.get("status", "").lower() == "active"]
            # If multiple names exist for an entity, we assume each record has been pre-filtered by the API.
            # For each active company, enrich with LEI information.
            for company in active_companies:
                lei = await fetch_lei_for_company(session, company)
                company["LEI"] = lei

            # Format the final output structure.
            job["companies"] = []
            for company in active_companies:
                job["companies"].append({
                    "companyName": company.get("name"),
                    "businessId": company.get("businessId"),
                    "companyType": company.get("companyForm"),  # TODO: Verify mapping for company type.
                    "registrationDate": company.get("registrationDate"),
                    "status": company.get("status"),
                    "LEI": company.get("LEI")
                })
            job["status"] = "completed"
            job["completedAt"] = datetime.datetime.utcnow().isoformat()

    except Exception as e:
        logging.exception("Error processing job %s", job["job_id"])
        job["status"] = "failed"
        job["error"] = str(e)

@app.route("/companies/search", methods=["POST"])
async def companies_search():
    # Parse the JSON payload from request.
    data = await request.get_json()
    if not data or "companyName" not in data:
        return jsonify({"error": "Missing required field: companyName"}), 400

    # Create a unique job id and record the request.
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()
    entity_jobs[job_id] = {"job_id": job_id, "status": "processing", "requestedAt": requested_at, "companies": None}

    # Fire and forget the processing task.
    asyncio.create_task(process_entity(entity_jobs[job_id], data))
    return jsonify({"resultId": job_id, "status": "processing", "message": "Your request is being processed."}), 202

@app.route("/companies/results/<job_id>", methods=["GET"])
async def companies_results(job_id):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if job["status"] != "completed":
        return jsonify({"resultId": job_id, "status": job["status"], "message": "Processing not finished, please try again later."}), 202
    return jsonify({
        "resultId": job_id,
        "companies": job["companies"]
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

------------------------------------------------------------

Notes:
• External API payloads and responses may require adjustments when the real API responses and data structures are available.
• The LEI enrichment function uses a placeholder and should be replaced with actual API communication as per your requirements.
• Persistence is simulated using an in‑memory cache (entity_jobs) for this prototype.
• Error handling is basic and can be enhanced in the full implementation.