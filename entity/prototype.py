Below is an example prototype.py file that implements a working prototype. In this code the POST endpoint performs external API calls (using aiohttp.ClientSession) to the Finnish Companies Registry and a placeholder for LEI enrichment. A simple in-memory dictionary serves as our local cache for job results. Where the external calls or processing details are not final, a TODO comment is provided.

--------------------------------------------------
# prototype.py

from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import aiohttp
import asyncio
import uuid
import time

app = Quart(__name__)
QuartSchema(app)  # add QuartSchema

# Simple in-memory persistence for jobs (job_id -> result)
job_results = {}

# Constants for external API endpoints (using provided details)
PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3"
COMPANY_ENDPOINT = f"{PRH_API_BASE}/companies"

# Placeholder URL for LEI lookup - TODO: replace with a real endpoint if available
LEI_API_BASE = "https://example.com/lei"  # TODO: Integrate with an actual LEI data source


async def get_prh_company_data(company_name: str):
    """
    Call the Finnish Companies Registry API using aiohttp.
    """
    params = {
        "name": company_name
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(COMPANY_ENDPOINT, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data  # Assuming this returns a list/dict of companies
                else:
                    # TODO: Improve error handling based on specific API response details.
                    return {"error": f"PRH API returned status {resp.status}"}
        except Exception as e:
            # TODO: Log exception
            return {"error": str(e)}


async def get_lei_for_company(company):
    """
    Retrieve the LEI for a given company.
    For now, we use a placeholder response. Replace with real logic as necessary.
    """
    # TODO: Replace with an actual request to a LEI API.
    async with aiohttp.ClientSession() as session:
        try:
            # Here we simulate an API call with a dummy request.
            # For example: GET LEI_API_BASE?businessId=<company_businessId>
            # Using a dummy sleep to simulate network delay.
            await asyncio.sleep(0.1)
            # TODO: Implement actual API call and parse result.
            # This is a placeholder that always returns a mock LEI.
            return "MOCK_LEI_12345"
        except Exception:
            return "Not Available"


async def process_query(job_id, payload):
    """
    Process the company search, filtering and LEI enrichment.
    """
    company_name = payload.get("companyName")
    if not company_name:
        job_results[job_id] = {"status": "failed", "error": "companyName is required"}
        return

    # 1. Retrieve company data from PRH API.
    prh_data = await get_prh_company_data(company_name)
    
    # Check for API error (assuming error key on failure)
    if isinstance(prh_data, dict) and prh_data.get("error"):
        job_results[job_id] = {"status": "failed", "error": prh_data["error"]}
        return

    # TODO: Adjust retrieval based on the actual structure of prh_data.
    companies = prh_data.get("results", [])  # Assuming results key contains the company data list

    # 2. Filter out inactive companies.
    # Assuming each company has a field "status" where "Active" signifies an active company.
    active_companies = [c for c in companies if c.get("status", "").lower() == "active"]

    # 3. Enrich each active company with LEI data.
    enriched_companies = []
    for comp in active_companies:
        lei = await get_lei_for_company(comp)
        enriched_company = {
            "companyName": comp.get("name", "Unknown"),
            "businessId": comp.get("businessId", "Unknown"),
            "companyType": comp.get("companyForm", "Unknown"),
            "registrationDate": comp.get("registrationDate", "Unknown"),
            "status": comp.get("status", "Unknown"),
            "lei": lei if lei else "Not Available"
        }
        enriched_companies.append(enriched_company)

    # Populate result cache with processed output
    job_results[job_id] = {
        "status": "completed",
        "completedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "results": enriched_companies
    }


@app.route('/companies/query', methods=['POST'])
async def company_query():
    """
    POST endpoint that performs external API queries, filtering and enrichment.
    """
    try:
        payload = await request.get_json()
    except Exception as e:
        return jsonify({"error": "Invalid JSON payload", "details": str(e)}), 400

    # Create a unique jobId
    job_id = str(uuid.uuid4())

    # Set initial job status as processing
    job_results[job_id] = {"status": "processing", "requestedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    # Launch the processing in the background
    asyncio.create_task(process_query(job_id, payload))

    return jsonify({
        "jobId": job_id,
        "status": "processing",
        "requestedAt": job_results[job_id]["requestedAt"]
    }), 202


@app.route('/companies/result/<job_id>', methods=['GET'])
async def get_result(job_id):
    """
    GET endpoint to retrieve final results using the job id.
    """
    result = job_results.get(job_id)
    if not result:
        return jsonify({"error": "Job ID not found"}), 404

    # If processing is still underway, return status
    return jsonify({"jobId": job_id, **result})


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

--------------------------------------------------

This prototype uses aiohttp for making HTTP requests and follows the specified endpoint design. The external API calls and persistence use mocks and in-memory storage with TODO comments indicating areas that require a proper implementation prior to final deployment.