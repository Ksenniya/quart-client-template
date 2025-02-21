Below is one acceptable refactoring of the code. In the refactored version the in‑memory “jobs” dictionary and any direct updates to it have been replaced by calls to the external service (entity_service). (If you need more fine‑grained operations than add_item/update_item/get_item, leave the rest of the business logic intact.) Note that we now use the entity_service add_item function in the POST endpoint to store the “job record” (here called with entity_model "companies_search") and later update it in the asynchronous task via update_item. Similarly, the GET endpoint retrieves the record via get_item. Also note that the required startup registrations (including calling init_cyoda) are added at the top. 

Below is the full refactored file:

-------------------------------------------------------------
#!/usr/bin/env python3
import asyncio
import csv
import uuid
from datetime import datetime
from io import StringIO
from dataclasses import dataclass

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring

# ------------------------------- Add external service dependencies
from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# -------------------------------
# Dataclasses for Request Validation

# For POST /companies/search: only validating a required companyName.
@dataclass
class CompanySearch:
    companyName: str

# For GET /companies/results: validating query parameters.
@dataclass
class CompanyQuery:
    searchId: str
    format: str = "json"

# -------------------------------
# Removed the in-memory jobs cache.
# All "job" data is now saved and read using the external entity_service.
# We use the job entity model "companies_search" for these records.

# -------------------------------
# Helper Functions

async def fetch_company_data(company_name: str, filters: dict) -> list:
    """
    Query the Finnish Companies Registry API using aiohttp.
    For now, only query by company name is implemented.
    TODO: Incorporate additional filters and proper error handling.
    """
    url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
    params = {"name": company_name}
    # TODO: Add additional parameters from filters if provided
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            data = await response.json()
            # Assuming data structure contains a key 'results' with list of companies.
            return data.get("results", [])

async def fetch_lei(company: dict) -> str:
    """
    Fetch the Legal Entity Identifier (LEI) for a given company.
    This is a placeholder and returns a mock value.
    TODO: Integrate with an official LEI API or other reliable data source.
    """
    await asyncio.sleep(0.1)  # Simulate network delay.
    if len(company.get("companyName", "")) % 2 == 0:
        return "FAKELEI1234567890"
    else:
        return "Not Available"

def filter_active_companies(companies: list) -> list:
    """
    Filter companies to retain only active ones.
    Assumes each company dict includes a 'businessStatus' field.
    TODO: Adjust condition based on the actual API response structure.
    """
    active = []
    for company in companies:
        if company.get("businessStatus", "").lower() == "active":
            active.append(company)
    return active

async def process_search(job_id: str, payload: dict):
    """
    Background task to process the search:
      1. Query external companies API.
      2. Filter out inactive companies.
      3. Enrich each active company with LEI information.
      4. Update the job record via entity_service.
    """
    try:
        # Extract search criteria. 'companyName' is validated via dataclass.
        company_name = payload.get("companyName", "")
        filters = payload.get("filters", {})  # Additional filtering criteria.
        
        # Step 1: Retrieve company data.
        companies = await fetch_company_data(company_name, filters)
        
        # Step 2: Filter inactive companies.
        active_companies = filter_active_companies(companies)
        
        # Step 3: Enrich each active company with LEI.
        enriched = []
        for comp in active_companies:
            lei = await fetch_lei(comp)
            enriched_company = {
                "companyName": comp.get("companyName", "Unknown"),
                "businessId": comp.get("businessId", "Unknown"),
                "companyType": comp.get("companyForm", "Unknown"),
                "registrationDate": comp.get("registrationDate", "Unknown"),
                "status": "Active",  # because they are filtered already.
                "lei": lei
            }
            enriched.append(enriched_company)
        
        await asyncio.sleep(0.1)  # Simulate any further processing delay.
        
        # Step 4: Update the processed result via entity_service.
        updated_job = {
            "status": "completed",
            "result": {
                "searchId": job_id,
                "companies": enriched
            }
        }
        entity_service.update_item(
            token=cyoda_token,
            entity_model="companies_search",
            entity_version=ENTITY_VERSION,
            entity=updated_job,
            meta={}
        )
    except Exception as e:
        # In case of error, update job record accordingly.
        updated_job = {
            "status": "error",
            "error": str(e)
        }
        entity_service.update_item(
            token=cyoda_token,
            entity_model="companies_search",
            entity_version=ENTITY_VERSION,
            entity=updated_job,
            meta={}
        )

# -------------------------------
# API Endpoints

@app.route('/companies/search', methods=['POST'])
@validate_request(CompanySearch)
@validate_response(dict, 202)
async def post_company_search(data: CompanySearch):
    """
    Accepts search criteria and triggers external API calls and data enrichment.
    POST endpoint with business logic and external data retrieval.
    Data is validated via the CompanySearch dataclass.
    """
    # If additional fields beyond 'companyName' are provided, fetch the raw data.
    payload = await request.get_json()
    if not payload:
        return jsonify({"error": "Invalid or missing JSON payload."}), 400

    # Instead of storing in a local dict, we store the job record with status "processing"
    requested_at = datetime.utcnow().isoformat()
    job_record = {
        "status": "processing",
        "requestedAt": requested_at
    }
    # Use entity_service.add_item to create the job record.
    job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies_search",
        entity_version=ENTITY_VERSION,
        entity=job_record  # the validated job record data
    )
    
    # Fire-and-forget asynchronous processing.
    asyncio.create_task(process_search(job_id, payload))
    
    return jsonify({
        "searchId": job_id,  # added id so that the user can query data by id
        "status": "processing",
        "requestedAt": requested_at
    }), 202

@app.route('/companies/results', methods=['GET'])
@validate_querystring(CompanyQuery)
async def get_company_results():
    """
    Retrieves stored search results.
    GET endpoint accepts query parameters which are validated via the CompanyQuery dataclass.
    """
    search_id = request.args.get("searchId")
    output_format = request.args.get("format", "json").lower()
    
    if not search_id:
        return jsonify({"error": "Missing searchId query parameter"}), 400
    
    # Instead of reading from local dict, we get the job record from entity_service.
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies_search",
        entity_version=ENTITY_VERSION,
        technical_id=search_id
    )
    if job is None:
        return jsonify({"error": "Invalid searchId"}), 404

    # If the processing is not complete, report the current status.
    if job.get("status") != "completed":
        return jsonify({"searchId": search_id, "status": job.get("status")}), 202
    
    result = job.get("result", {})
    
    # If CSV is requested, convert the result to CSV format.
    if output_format == "csv":
        si = StringIO()
        cw = csv.writer(si)
        headers = ["companyName", "businessId", "companyType", "registrationDate", "status", "lei"]
        cw.writerow(headers)
        for company in result.get("companies", []):
            cw.writerow([
                company.get("companyName"),
                company.get("businessId"),
                company.get("companyType"),
                company.get("registrationDate"),
                company.get("status"),
                company.get("lei")
            ])
        return app.response_class(si.getvalue(), mimetype='text/csv')
    
    # Default to JSON output.
    return jsonify(result), 200

# -------------------------------
# Mermaid Diagram Representation (documentation purposes only)
mermaid_diagram = """
sequenceDiagram
    participant Client as Client App
    participant API as Backend API
    participant PRH as Finnish Companies Registry API
    participant LEI as External LEI Service
    participant ExternalService as External Entity Service

    Client->>API: POST /companies/search {companyName, filters...}
    API->>ExternalService: add_item( status="processing" )
    API->>PRH: Request company data based on criteria
    PRH-->>API: Return company data
    API->>API: Filter inactive companies
    loop For each active company
      API->>LEI: Request LEI details
      LEI-->>API: Return LEI or "Not Available"
    end
    API->>ExternalService: update_item( status="completed", result=... )
    API-->>Client: Return searchId and status ("processing")
    Client->>API: GET /companies/results?searchId=xxx&format=json
    API->>ExternalService: get_item(searchId)
    API-->>Client: Return final search result (JSON or CSV)
"""

# -------------------------------
# Entry Point
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

# End of prototype.py
-------------------------------------------------------------

Key changes made:
1. All direct access to the local jobs cache has been removed.
2. The POST endpoint now creates a job record by calling entity_service.add_item and returns the id (searchId) in the response.
3. The process_search background task calls entity_service.update_item to update the job record once processing completes (or errors occur).
4. The GET endpoint retrieves a job record using entity_service.get_item.
5. The startup() function now calls init_cyoda(cyoda_token) before serving, as requested.

This refactoring preserves all the business logic (fetching company data, filtering companies, enriching with LEI, and output formatting) while replacing local state management with interactions via the external entity_service.