Below is an example implementation for prototype.py. This prototype uses Quart with QuartSchema (but without @validate_request), aiohttp for external HTTP calls, and a simple in‑memory cache for persistence. Any unclear external calls are replaced with mocks (with TODO comments).

--------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from quart import Quart, request, jsonify, Response
from quart_schema import QuartSchema
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# In-memory cache for job persistence (mock persistence)
entity_jobs = {}

# Constants for external API endpoints
PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3"
# TODO: Replace with real external LEI data source URL when known.
LEI_API_URL = "https://example.com/lei"  # Placeholder URL

async def fetch_companies(session: aiohttp.ClientSession, company_name: str, filters: dict) -> dict:
    """
    Calls the Finnish Companies Registry API with the given company name and filters.
    """
    params = {"name": company_name}
    # TODO: Add additional parameters from filters if required.
    url = f"{PRH_API_BASE}/companies"
    async with session.get(url, params=params) as resp:
        # Basic error handling; in a production app you'd handle status codes, etc.
        if resp.status != 200:
            # TODO: Use proper error handling and logging.
            return {"companies": []}
        return await resp.json()


async def fetch_lei_for_company(session: aiohttp.ClientSession, company: dict) -> str:
    """
    Mocks external LEI lookup for a given company.
    In production, call the actual LEI API or a reliable source.
    """
    # TODO: Replace this mock with an actual API call to fetch LEI.
    # Simulate network delay
    await asyncio.sleep(0.2)
    # For demonstration, return a mock LEI if the company is active
    if company.get("status", "").lower() == "active":
        return "MOCK_LEI_12345"
    return "Not Available"


async def process_entity(job_id: str, data: dict):
    """
    Processing function that performs external API calls, filtering,
    and LEI enrichment. Updates the job in the in-memory cache.
    """
    async with aiohttp.ClientSession() as session:
        # 1. Retrieve companies from Finnish Companies Registry API
        company_name = data.get("companyName")
        filters = data.get("filters", {})
        companies_data = await fetch_companies(session, company_name, filters)
        companies = companies_data.get("companies", [])
        
        # 2. Filter out inactive companies.
        active_companies = []
        for comp in companies:
            # Assuming "status" field indicates business status
            if comp.get("status", "").lower() == "active":
                active_companies.append(comp)
        
        # 3. Enrich data with LEI information (for each active company)
        enriched_companies = []
        for comp in active_companies:
            lei = await fetch_lei_for_company(session, comp)
            # Create a unified structure for each company
            enriched_company = {
                "companyName": comp.get("companyName", "Unknown"),
                "businessId": comp.get("businessId", "Unknown"),
                "companyType": comp.get("companyType", "Unknown"),
                "registrationDate": comp.get("registrationDate", "Unknown"),
                "status": "Active",
                "lei": lei
            }
            enriched_companies.append(enriched_company)
        
        # 4. Update the in-memory cache with the enriched results.
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = enriched_companies


@app.route("/companies/search", methods=["POST"])
async def companies_search():
    """
    Endpoint to search for companies, filter inactive ones,
    enrich them with LEI, and store the result.
    All expensive work (external API calls, enrichment) is done here.
    """
    data = await request.get_json()
    if not data or "companyName" not in data:
        return jsonify({"error": "Missing companyName in request"}), 400
    
    # Generate a unique job_id and store initial job details
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat() + "Z"
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}
    
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, data))
    
    # Return the job_id so the user can poll for results.
    return jsonify({"resultId": job_id, "status": "processing"}), 202


@app.route("/companies/result/<job_id>", methods=["GET"])
async def companies_result(job_id):
    """
    Endpoint to retrieve results for a given job_id.
    """
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Result ID not found"}), 404
    
    if job["status"] != "completed":
        return jsonify({"resultId": job_id, "status": job["status"]}), 202

    # Return the enriched result.
    # Check if the caller wants CSV instead of JSON (this is a basic simulation).
    output_format = request.args.get("outputFormat", "json").lower()
    if output_format == "csv":
        # TODO: Implement a proper CSV conversion if required.
        csv_data = "companyName,businessId,companyType,registrationDate,status,lei\n"
        for comp in job["result"]:
            csv_row = f'{comp["companyName"]},{comp["businessId"]},{comp["companyType"]},' \
                      f'{comp["registrationDate"]},{comp["status"]},{comp["lei"]}\n'
            csv_data += csv_row
        return Response(csv_data, mimetype="text/csv")
    
    return jsonify({"resultId": job_id, "status": job["status"], "companies": job["result"]})


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

--------------------------------------------------

Notes:
• The Finnish Companies API call uses GET with aiohttp.ClientSession to fetch company data. Filters beyond companyName are placeholders.
• The LEI retrieval is mocked with a short delay and returns a fixed value. A TODO comment indicates where a real API call should occur.
• Persistence is handled via the in-memory dictionary entity_jobs.
• The code uses asynchronous processing (via asyncio.create_task) to allow immediate response from POST and background job processing.
• CSV conversion in GET is basic and marked with a TODO if more advanced formatting is required.