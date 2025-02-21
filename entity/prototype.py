Below is an updated prototype.py that uses dataclasses along with the quart-schema decorators. Note that we use simple dataclasses with only primitive types for validation. For the POST endpoint we’ve defined a request and response schema, whereas the GET endpoint (which uses a path parameter only) does not require additional validation.

----------------------------------------------------------------
# prototype.py

from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response  # and validate_querystring if needed
import aiohttp
import asyncio
import uuid
import time

app = Quart(__name__)
QuartSchema(app)  # initialize QuartSchema

# In-memory job storage: job_id -> result
job_results = {}

# External API endpoint constants
PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3"
COMPANY_ENDPOINT = f"{PRH_API_BASE}/companies"
# Placeholder for LEI lookup endpoint (to be replaced with a real endpoint)
LEI_API_BASE = "https://example.com/lei"  # TODO: Integrate with an actual LEI data source

# --- Dataclass Definitions for Validation ---

@dataclass
class CompanyQueryRequest:
    companyName: str
    outputFormat: str = "json"  # json or csv

@dataclass
class QueryResponse:
    jobId: str
    status: str
    requestedAt: str

# --- Helper functions ---

async def get_prh_company_data(company_name: str):
    """
    Make an http GET request to the Finnish Companies Registry API using aiohttp.
    """
    params = {"name": company_name}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(COMPANY_ENDPOINT, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data  # TODO: Adjust based on the actual response structure.
                else:
                    # TODO: Improve error handling based on specific API responses.
                    return {"error": f"PRH API returned status {resp.status}"}
        except Exception as e:
            # TODO: Log exception details.
            return {"error": str(e)}

async def get_lei_for_company(company):
    """
    Retrieve the LEI for the given company.
    This is a placeholder implementation.
    """
    # TODO: Replace with an actual API call to a trusted LEI source.
    async with aiohttp.ClientSession() as session:
        try:
            # Simulate a network call delay.
            await asyncio.sleep(0.1)
            # TODO: Implement actual external call logic here.
            return "MOCK_LEI_12345"
        except Exception:
            return "Not Available"

async def process_query(job_id: str, payload: dict):
    """
    Retrieve company data, filter inactive companies, enrich with LEI and cache the output.
    """
    company_name = payload.get("companyName")
    if not company_name:
        job_results[job_id] = {"status": "failed", "error": "companyName is required"}
        return

    # 1. Retrieve data from the Finnish Companies Registry API
    prh_data = await get_prh_company_data(company_name)
    if isinstance(prh_data, dict) and prh_data.get("error"):
        job_results[job_id] = {"status": "failed", "error": prh_data["error"]}
        return

    # TODO: Adjust this extraction based on the actual API response structure
    companies = prh_data.get("results", [])

    # 2. Filter out inactive companies – assuming 'status' field holds the value.
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

    # Store the final result in the in-memory cache
    job_results[job_id] = {
        "status": "completed",
        "completedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "results": enriched_companies
    }

# --- Endpoints ---

@app.route('/companies/query', methods=['POST'])
@validate_request(CompanyQueryRequest)  # This should be the second decorator in POST endpoints.
@validate_response(QueryResponse, 202)
async def company_query(data: CompanyQueryRequest):
    """
    POST endpoint that triggers external API calls, filtering and enrichment.
    """
    # Create a unique job ID and store initial processing state.
    job_id = str(uuid.uuid4())
    requested_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    job_results[job_id] = {"status": "processing", "requestedAt": requested_at}

    # Fire and forget the processing task.
    asyncio.create_task(process_query(job_id, data.__dict__))

    return QueryResponse(jobId=job_id, status="processing", requestedAt=requested_at), 202

@app.route('/companies/result/<job_id>', methods=['GET'])
async def get_result(job_id: str):
    """
    GET endpoint that returns the processed results for the given job ID.
    """
    result = job_results.get(job_id)
    if not result:
        return jsonify({"error": "Job ID not found"}), 404

    return jsonify({"jobId": job_id, **result})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

----------------------------------------------------------------

In this prototype:
• The POST endpoint (/companies/query) uses @validate_request with the CompanyQueryRequest dataclass and @validate_response with QueryResponse.
• The GET endpoint (/companies/result/<job_id>) does not perform body validation as it only uses a path parameter.
• Wherever a detail remains uncertain (e.g., structure of the PRH API response and LEI API lookup), TODO comments have been added.
• aiohttp.ClientSession is used for making external HTTP requests.
• In-memory caching (job_results dictionary) serves as a placeholder for persistence.

This should let you verify the user experience and highlight any further requirements.