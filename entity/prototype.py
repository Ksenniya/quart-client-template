#!/usr/bin/env python3
import asyncio
import aiohttp
import uuid
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring

# Initialize the Quart app and schema.
app = Quart(__name__)
QuartSchema(app)

# In-memory persistence for search jobs.
entity_jobs = {}

# External API endpoints (placeholders, adjust if needed)
PRH_API_URL = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
LEI_API_URL = "https://example.com/lei"  # TODO: Replace with an official LEI registry endpoint.

# Dataclass for POST search request validation
@dataclass
class CompanySearch:
    companyName: str
    location: Optional[str] = None
    businessId: Optional[str] = None
    companyForm: Optional[str] = None
    registrationDateStart: Optional[str] = None
    registrationDateEnd: Optional[str] = None

# Dataclass for POST search response validation
@dataclass
class SearchResponse:
    searchId: str
    message: str

# POST endpoint: Note the decorator order is a workaround for quart-schema issues:
# For POST endpoints, @app.route comes first, then @validate_request, then @validate_response.
@app.route("/api/companies/search", methods=["POST"])
@validate_request(CompanySearch)  # Works as expected for POST requests.
@validate_response(SearchResponse, 202)
async def search_companies(data: CompanySearch):
    # Use validated data from CompanySearch dataclass.
    if not data.companyName:
        return jsonify({"error": "companyName is required"}), 400

    # Generate a new search ID and register the job.
    search_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"
    entity_jobs[search_id] = {"status": "processing", "requestedAt": requested_at, "result": None}

    # Fire and forget the processing task.
    asyncio.create_task(process_search(search_id, data))
    return SearchResponse(searchId=search_id, message="Processing started"), 202

async def process_search(search_id, criteria: CompanySearch):
    try:
        async with aiohttp.ClientSession() as session:
            # Build query parameters based on provided criteria.
            params = {"name": criteria.companyName}
            if criteria.location:
                params["location"] = criteria.location
            if criteria.businessId:
                params["businessId"] = criteria.businessId
            if criteria.companyForm:
                params["companyForm"] = criteria.companyForm
            if criteria.registrationDateStart:
                params["registrationDateStart"] = criteria.registrationDateStart
            if criteria.registrationDateEnd:
                params["registrationDateEnd"] = criteria.registrationDateEnd

            # Call the Finnish Companies Registry API (PRH API).
            async with session.get(PRH_API_URL, params=params) as resp:
                if resp.status != 200:
                    # TODO: Improve error handling when fetching data from PRH API.
                    companies_data = {"results": []}
                else:
                    companies_data = await resp.json()

            # TODO: Adjust filtering based on the actual data structure from PRH API.
            active_companies = []
            for company in companies_data.get("results", []):
                # Assuming the PRH API returns a field "status" that indicates if a company is active.
                if company.get("status", "").lower() == "active":
                    active_companies.append(company)

            enriched_companies = []
            # For each active company, enrich data with LEI information.
            for comp in active_companies:
                lei = await fetch_lei(session, comp)
                enriched_companies.append({
                    "companyName": comp.get("name", "Unknown"),
                    "businessId": comp.get("businessId", "Unknown"),
                    "companyType": comp.get("companyType", "Unknown"),  # TODO: Verify field name.
                    "registrationDate": comp.get("registrationDate", "Unknown"),
                    "status": "Active",
                    "LEI": lei if lei else "Not Available"
                })

            result = {
                "searchId": search_id,
                "retrievedAt": datetime.utcnow().isoformat() + "Z",
                "companies": enriched_companies
            }
            entity_jobs[search_id]["result"] = result
            entity_jobs[search_id]["status"] = "completed"
    except Exception as e:
        logging.exception("Error processing search")
        entity_jobs[search_id]["status"] = "failed"
        entity_jobs[search_id]["error"] = str(e)

async def fetch_lei(session, company):
    # Placeholder function to simulate LEI lookup.
    # TODO: Replace with an actual lookup against a valid LEI data source.
    await asyncio.sleep(0.1)  # Simulated network delay
    business_id = company.get("businessId", "")
    # For demonstration, return a mock LEI if the businessId ends with an even digit.
    if business_id and business_id[-1] in "02468":
        return "5493001KJTIIGC8Y1R12"  # Example LEI
    return None

# GET endpoint for retrieving processed search results.
# No request body or query parameters; standard route without validation.
@app.route("/api/companies/<search_id>", methods=["GET"])
async def get_search_result(search_id):
    job = entity_jobs.get(search_id)
    if not job:
        abort(404, description="Search ID not found")
    if job["status"] == "processing":
        return jsonify({"status": "processing", "message": "Results are not ready yet. Please try again later."}), 202
    elif job["status"] == "failed":
        return jsonify({"status": "failed", "error": job.get("error", "Unknown error occurred")}), 500
    return jsonify(job["result"]), 200

# Mermaid diagrams as comments for developer reference:

"""
Sequence Diagram:
--------------------------------------------------
sequenceDiagram
    participant U as User
    participant A as Application
    participant PRH as PRH API (Finnish Companies Registry)
    participant LEI as LEI Data Source

    U->>A: POST /api/companies/search (with search criteria)
    A->>PRH: GET companies?name=... (&filters)
    PRH-->>A: List of matching companies
    A->>A: Filter for active companies
    loop For each active company
        A->>LEI: Request LEI information
        LEI-->>A: Return LEI data (or "Not Available")
    end
    A->>U: Respond with searchId and initial status

User Journey Diagram:
--------------------------------------------------
journey
  title User Journey for Company Data Enrichment
  section Initiate Search
    Enter search criteria: 5: User, Application
    Submit search request (POST /api/companies/search): 5: User, Application
  section Wait and Retrieve
    System processes search & enrichment: 4: Application, External APIs
    Poll for results using searchId (GET /api/companies/{searchId}): 3: User, Application
  section View Results
    View and validate enriched company data: 5: User, Application
"""

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)