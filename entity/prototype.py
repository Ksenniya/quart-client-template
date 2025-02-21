Below is an example prototype.py that uses Quart and aiohttp. This prototype follows the finalized API design and uses a local in-memory dictionary (jobs) as a mock persistence layer. Any areas where the requirements are unclear (such as exact response structure from external APIs or the real LEI lookup) have been marked with TODO comments.

-------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# In-memory store for job results
jobs = {}

async def fetch_company_data(company_name: str, filters: dict) -> dict:
    """
    Query the Finnish Companies Registry API.
    TODO: Adjust request parameters and response parsing based on actual API contract.
    """
    url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
    # Build query parameters: mandatory company name with any provided filters
    params = {"name": company_name}
    params.update(filters)
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                # TODO: Adapt the parsing based on actual API response structure.
                return data
            else:
                # Log error and return empty companies list
                # TODO: Add proper error handling/logging.
                return {"companies": []}

async def fetch_lei(company: dict) -> str:
    """
    Fetch the Legal Entity Identifier (LEI) for the given company.
    This is currently a mock implementation.
    TODO: Replace with a real external call to official LEI registries or reliable data sources.
    """
    await asyncio.sleep(0.1)  # Simulate network delay
    # A simple mock: if company has a name, return a fake LEI; otherwise, return "Not Available"
    if company.get("companyName"):
        return "MOCK_LEI_123456789"
    return "Not Available"

async def process_entity(job_id: str, criteria: dict):
    """
    Process the entity by retrieving, filtering, and enriching company data.
    """
    company_name = criteria.get("companyName")
    filters = criteria.get("filters", {})
    # Retrieve data from the Finnish Companies Registry
    companies_response = await fetch_company_data(company_name, filters)
    # Assuming companies_response contains a "companies" key with a list of companies.
    companies = companies_response.get("companies", [])
    # Filter out inactive companies. Assuming "status" field indicates business status.
    active_companies = [comp for comp in companies if comp.get("status", "").lower() == "active"]
    
    enriched_companies = []
    for company in active_companies:
        lei = await fetch_lei(company)
        enriched_company = {
            "companyName": company.get("companyName"),
            "businessId": company.get("businessId"),
            "companyType": company.get("companyForm"),  # Mapping companyForm as companyType
            "registrationDate": company.get("registrationDate"),
            "status": company.get("status"),
            "lei": lei if lei else "Not Available"
        }
        enriched_companies.append(enriched_company)
    
    # Update the job in the local cache once processing is complete
    jobs[job_id] = {
        "status": "completed",
        "requestedAt": datetime.datetime.utcnow().isoformat(),
        "data": enriched_companies
    }

@app.route("/companies/enrich", methods=["POST"])
async def enrich_companies():
    """
    Endpoint that accepts search criteria, processes external API calls, and triggers data enrichment.
    It returns immediately with a job ID while processing occurs in the background.
    """
    criteria = await request.get_json()
    job_id = str(uuid.uuid4())
    # Store initial job state in the in-memory cache.
    jobs[job_id] = {"status": "processing", "requestedAt": datetime.datetime.utcnow().isoformat()}
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, criteria))
    
    response = {
        "requestId": job_id,
        "status": "processing",
        "message": "Job started",
        "data": []  # Initially empty; real data will be available via GET /companies/results.
    }
    return jsonify(response)

@app.route("/companies/results", methods=["GET"])
async def get_results():
    """
    Endpoint to retrieve results from a previously started enrich job using the requestId.
    """
    job_id = request.args.get("requestId")
    if not job_id:
        return jsonify({"error": "Missing requestId parameter"}), 400
    result = jobs.get(job_id)
    if not result:
        return jsonify({"error": "Job not found"}), 404
    
    response = {
        "requestId": job_id,
        "status": result.get("status"),
        "message": "Job completed" if result.get("status") == "completed" else "Job processing",
        "data": result.get("data", [])
    }
    return jsonify(response)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
-------------------------------------------------

This prototype uses aiohttp for asynchronous HTTP requests to external APIs, mocks persistence with a local dictionary, and leverages Quart for the web framework. The placeholders marked with TODO should be revisited once the detailed requirements (such as exact API responses and external data source endpoints) are confirmed.