Below is the updated prototype.py file. In this version we define dataclasses for the search request and response payloads and include @validate_request and @validate_response for the POST endpoint. (Note that for GET endpoints—if we ever had query string validation—the decorator is placed before @app.route. This is a known workaround for an issue with quart-schema.)

------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
import aiohttp

from dataclasses import dataclass
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response  # for GET, use validate_querystring if needed (see comment below)

app = Quart(__name__)
QuartSchema(app)

# In-memory persistence for job results (a prototype-local cache)
entity_jobs = {}

# Define data classes for request/response objects

@dataclass
class CompanySearchRequest:
    companyName: str
    # Optional fields for future expansion (only primitives)
    registrationDateFrom: str = ""
    registrationDateTo: str = ""

@dataclass
class CompanyRecord:
    companyName: str
    businessId: str
    companyType: str
    registrationDate: str
    status: str
    lei: str

@dataclass
class CompanySearchResponse:
    searchId: str
    results: list  # List of CompanyRecord objects (using only primitives)

# Asynchronous function to call the Finnish Companies Registry API
async def fetch_prh_data(company_name: str) -> dict:
    """Calls the Finnish Companies Registry API and returns JSON data."""
    prh_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
    params = {"name": company_name}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(prh_url, params=params) as resp:
                if resp.status != 200:
                    # TODO: Add proper error handling and logging if needed.
                    return {}  # Return empty dict on error for prototype
                data = await resp.json()
                return data
        except Exception as e:
            # TODO: Log the exception properly.
            return {}

# Asynchronous function to fetch the LEI data.
async def fetch_lei_data(company: dict) -> str:
    """Fetches the LEI for a given company using an external LEI API.
       This is a placeholder that simulates the LEI lookup.
    """
    # TODO: Replace with actual LEI data source call when available.
    await asyncio.sleep(0.1)  # simulate network delay
    try:
        if int(company.get("businessId", "0")[-1]) % 2 == 0:
            return "5493001KJTIIGC8Y1R12"
    except Exception:
        pass
    return "Not Available"

# Asynchronous processing function that retrieves, filters, and enriches company data.
async def process_entity(job_id: str, input_data: dict):
    """Process the retrieval, filtering, and LEI enrichment.
       This function is executed asynchronously after accepting a job.
    """
    results = []
    company_name = input_data.get("companyName")
    
    # Call the Finnish Companies Registry API.
    prh_response = await fetch_prh_data(company_name)
    
    # TODO: Adjust below based on real API response structure.
    companies = prh_response.get("results", []) if prh_response else []
    
    # Filtering out inactive companies.
    active_companies = []
    for company in companies:
        # TODO: Replace with the actual field or logic to determine active status.
        if company.get("status", "").lower() == "active":
            active_companies.append(company)
    
    # Enrich active companies with LEI data.
    for company in active_companies:
        lei = await fetch_lei_data(company)
        enriched = {
            "companyName": company.get("companyName", "Unknown"),
            "businessId": company.get("businessId", "Unknown"),
            "companyType": company.get("companyType", "Unknown"),
            "registrationDate": company.get("registrationDate", "Unknown"),
            "status": "Active",
            "lei": lei
        }
        results.append(enriched)
    
    # Update the job record in the in-memory cache.
    entity_jobs[job_id]["status"] = "completed"
    entity_jobs[job_id]["results"] = results

# POST endpoint: process external calls and store resulting enriched company data.
@app.route("/companies/search", methods=["POST"])
@validate_request(CompanySearchRequest)  # For POST requests, place after @app.route (workaround for quart-schema issue)
@validate_response(CompanySearchResponse, 200)
async def search_companies(data: CompanySearchRequest):
    """Initiate company search and enrichment."""
    company_name = data.companyName
    if not company_name:
        abort(400, description="Missing required field: companyName")
    
    # Create a unique job id and note the requested time.
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat() + "Z"
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": requested_at,
        "results": []
    }
    
    # Fire and forget the processing task.
    # TODO: In production, add better task handling and error logging.
    asyncio.create_task(process_entity(job_id, data.__dict__))
    
    # Immediate response with searchId; results may be pending.
    return CompanySearchResponse(searchId=job_id, results=[])

# GET endpoint: Retrieve processed search results using a path parameter.
# Note: No validation is applied here because we are not expecting a query string.
@app.route("/companies/results/<job_id>", methods=["GET"])
async def get_results(job_id):
    """Retrieve stored enriched results by searchId."""
    job = entity_jobs.get(job_id)
    if not job:
        abort(404, description="Job ID not found.")
    
    response = {
        "searchId": job_id,
        "results": job.get("results"),
        "status": job.get("status"),
        "requestedAt": job.get("requestedAt")
    }
    return jsonify(response)

# A simple test endpoint for checking service health.
@app.route("/", methods=["GET"])
async def index():
    return "Finnish Companies Data Retrieval and Enrichment Prototype is running."

if __name__ == '__main__':
    # Entry point as specified.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

------------------------------------------------

Below is an updated Mermaid sequence diagram for the interaction:

------------------------------------------------
%% Mermaid Sequence Diagram
sequenceDiagram
    participant Client
    participant Server as "Quart App"
    participant PRH_API as "Finnish Registry API"
    participant LEI_API as "LEI Service"

    Client->>Server: POST /companies/search {companyName: "Example Corp"}
    Server->>PRH_API: GET /companies?name=Example+Corp
    PRH_API-->>Server: Company data (multiple companies)
    Server->>Server: Filter out inactive companies
    loop For each active company
      Server->>LEI_API: Request LEI for company
      LEI_API-->>Server: Return LEI (or "Not Available")
    end
    Server-->>Client: Response {searchId:"...", results:[]}
    Client->>Server: GET /companies/results/{searchId}
    Server-->>Client: Stored results with enriched data
------------------------------------------------

This prototype implements the earlier specified design. Future iterations would add robust error handling, persistence beyond an in-memory cache, and integration with actual external API endpoints.