#!/usr/bin/env python3
import asyncio
import aiohttp
import uuid
import logging
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional

from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response

from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

# Initialize external services before serving requests.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# External API endpoints (placeholders, adjust if needed)
PRH_API_URL = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
LEI_API_URL = "https://example.com/lei"  # TODO: Replace with an official LEI registry endpoint.

# Dataclass for validating POST request payload for company search.
@dataclass
class CompanySearch:
    companyName: str
    location: Optional[str] = None
    businessId: Optional[str] = None
    companyForm: Optional[str] = None
    registrationDateStart: Optional[str] = None
    registrationDateEnd: Optional[str] = None

# Dataclass for validating POST response.
@dataclass
class SearchResponse:
    searchId: str
    message: str

# Workflow function for search_job entities.
# This function is applied asynchronously to the entity before it is persisted.
# It performs external API calls and enriches the entity with the search result.
async def process_search_job(entity):
    try:
        # Get the search criteria stored in the entity
        criteria = entity.get("criteria", {})
        # Build query parameters for the PRH API based on search criteria.
        params = {"name": criteria.get("companyName", "")}
        if criteria.get("location"):
            params["location"] = criteria["location"]
        if criteria.get("businessId"):
            params["businessId"] = criteria["businessId"]
        if criteria.get("companyForm"):
            params["companyForm"] = criteria["companyForm"]
        if criteria.get("registrationDateStart"):
            params["registrationDateStart"] = criteria["registrationDateStart"]
        if criteria.get("registrationDateEnd"):
            params["registrationDateEnd"] = criteria["registrationDateEnd"]

        async with aiohttp.ClientSession() as session:
            # Call the PRH API to get companies based on the search criteria.
            async with session.get(PRH_API_URL, params=params) as resp:
                if resp.status != 200:
                    # In case of error, simulate an empty result.
                    companies_data = {"results": []}
                else:
                    companies_data = await resp.json()

            # Filter companies with active status.
            active_companies = []
            for company in companies_data.get("results", []):
                if company.get("status", "").lower() == "active":
                    active_companies.append(company)

            # Enrich the active companies with LEI data.
            enriched_companies = []
            for comp in active_companies:
                lei = await fetch_lei(session, comp)
                enriched_companies.append({
                    "companyName": comp.get("name", "Unknown"),
                    "businessId": comp.get("businessId", "Unknown"),
                    "companyType": comp.get("companyType", "Unknown"),  # TODO: Verify actual field name if needed.
                    "registrationDate": comp.get("registrationDate", "Unknown"),
                    "status": "Active",
                    "LEI": lei if lei else "Not Available"
                })

            result = {
                "searchId": entity["id"],
                "retrievedAt": datetime.utcnow().isoformat() + "Z",
                "companies": enriched_companies
            }

            # Update the entity state directly without calling add/update on the same entity.
            entity["status"] = "completed"
            entity["result"] = result
            entity["workflowProcessedAt"] = datetime.utcnow().isoformat() + "Z"
    except Exception as e:
        logging.exception("Error in process_search_job workflow")
        entity["status"] = "failed"
        entity["error"] = str(e)
    # Return entity is not used by entity_service but workflow modifies the entity in place.
    return entity

# Helper function to simulate fetching LEI information.
async def fetch_lei(session, company):
    try:
        # Simulate network delay for LEI lookup.
        await asyncio.sleep(0.1)
        business_id = company.get("businessId", "")
        if business_id and business_id[-1] in "02468":
            return "5493001KJTIIGC8Y1R12"  # Example LEI
    except Exception as e:
        logging.exception("Error fetching LEI")
    return None

# POST endpoint for initiating a company search.
# The controller logic is slim, handing over processing to the workflow function.
@app.route("/api/companies/search", methods=["POST"])
@validate_request(CompanySearch)
@validate_response(SearchResponse, 202)
async def search_companies(data: CompanySearch):
    if not data.companyName:
        return jsonify({"error": "companyName is required"}), 400

    # Generate a unique search ID and record the timestamp.
    search_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"
    # Include search criteria in the persisted entity so the workflow can use them.
    job_data = {
        "id": search_id,
        "status": "processing",
        "requestedAt": requested_at,
        "result": None,
        "criteria": asdict(data)
    }
    # Persist the entity using the add_item method with workflow processing.
    # The workflow function process_search_job will be invoked asynchronously before persistence.
    entity_service.add_item(
        token=cyoda_token,
        entity_model="search_job",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_data,
        workflow=process_search_job  # The workflow function that processes the search.
    )
    # Return initial response with searchId.
    return SearchResponse(searchId=search_id, message="Processing started"), 202

# GET endpoint for retrieving search results.
@app.route("/api/companies/<search_id>", methods=["GET"])
async def get_search_result(search_id):
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="search_job",
        entity_version=ENTITY_VERSION,
        technical_id=search_id
    )
    if not job:
        abort(404, description="Search ID not found")
    if job.get("status") == "processing":
        return jsonify({"status": "processing", "message": "Results are not ready yet. Please try again later."}), 202
    elif job.get("status") == "failed":
        return jsonify({"status": "failed", "error": job.get("error", "Unknown error occurred")}), 500
    return jsonify(job.get("result")), 200

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
    A->>A: Persist search_job entity with criteria & invoke workflow
    A->>PRH: GET companies?name=... (&filters) [within workflow]
    PRH-->>A: List of matching companies
    A->>A: Filter for active companies & enrich with LEI (within workflow)
    A->>U: Respond with searchId and initial status

User Journey Diagram:
--------------------------------------------------
journey
  title User Journey for Company Data Enrichment
  section Initiate Search
    Enter search criteria: 5: User, Application
    Submit search request (POST /api/companies/search): 5: User, Application
  section Processing
    Workflow function processes search & enrichment asynchronously: 4: Application, External APIs
  section Retrieve Result
    Poll for results using searchId (GET /api/companies/{searchId}): 3: User, Application
  section View Results
    View and validate enriched company data: 5: User, Application
"""

if __name__ == '__main__':
    # Run the application with debug and threaded mode settings.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)