Below is an example of how you can simplify the controller (endpoint) logic by moving most of the asynchronous processing into the workflow function. Instead of the controller launching a background task, the workflow function now handles the enrichment logic (fire‐and‐forget behavior) by updating the entity directly. This reduces the complexity of the endpoint and makes the code more robust. Note that the workflow function MUST modify the entity in place; it must not call add_item/update_item on the same entity.

For example, see the updated complete file below:

-------------------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from dataclasses import dataclass
from quart import Quart, jsonify
import aiohttp
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring

# Import constant and external services.
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)

# Startup routine to initialize the external cyoda service.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Dataclass for POST request validation.
@dataclass
class CompanySearchInput:
    companyName: str
    registrationDateStart: str = ""  # Optional; format: yyyy-mm-dd
    registrationDateEnd: str = ""    # Optional; format: yyyy-mm-dd

# ------------------ External API Calls ------------------

async def fetch_company_data(company_name, filters):
    url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
    params = {'name': company_name}
    if filters:
        params.update(filters)
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                return await resp.json()
            # Simple error handling; production use might require enhanced logic.
            return {"results": []}

async def fetch_lei_for_company(business_id):
    # Simulate a network delay and return a fake LEI based on business_id.
    await asyncio.sleep(0.1)
    if business_id and business_id[-1] in "02468":
        return "529900T8BM49AURSDO55"
    return "Not Available"

# ------------------ Workflow Function ------------------
#
# This function encapsulates all the asynchronous tasks that process
# and enrich the company search entity before it is persisted.
#
# IMPORTANT: This function must update the entity directly; do not call
# entity_service.add/update/delete on the entity of the same entity_model.
async def process_companies_search(entity):
    # Use the data stored in the entity – no need to re-read request parameters
    company_name = entity.get("companyName")
    
    # Build filters based on available entity attributes.
    filters = {}
    if entity.get("registrationDateStart"):
        filters["registrationDateStart"] = entity["registrationDateStart"]
    if entity.get("registrationDateEnd"):
        filters["registrationDateEnd"] = entity["registrationDateEnd"]

    # Retrieve and process company data.
    company_data = await fetch_company_data(company_name, filters)
    results = company_data.get("results", [])
    
    # Filter out active companies.
    active_companies = []
    for company in results:
        if company.get("status", "").lower() in ("active", ""):
            active_companies.append(company)

    enriched_results = []
    for company in active_companies:
        # Extract data; provide defaults if not found.
        name = company.get("name", "Unknown")
        business_id = company.get("businessId", "Unknown")
        company_type = company.get("companyForm", "Unknown")
        registration_date = company.get("registrationDate", "Unknown")
        lei = await fetch_lei_for_company(business_id)
        enriched_results.append({
            "companyName": name,
            "businessId": business_id,
            "companyType": company_type,
            "registrationDate": registration_date,
            "status": "Active",
            "lei": lei
        })

    # Update the entity in place; this new state will be persisted.
    entity["status"] = "completed"
    entity["results"] = enriched_results

    # Optionally, you may add a 'processedAt' timestamp.
    entity["processedAt"] = datetime.datetime.utcnow().isoformat()

    # Note: Do not call add_item/update_item for this entity model here.
    return entity

# ------------------ Endpoint Handlers ------------------

# POST endpoint to initiate the search process.
# The entire data enrichment task is now delegated to the workflow function.
@app.route('/companies/search', methods=['POST'])
@validate_request(CompanySearchInput)
@validate_response(dict, 200)
async def search_companies(data: CompanySearchInput):
    if not data.companyName:
        return jsonify({"error": "companyName is required"}), 400

    requested_at = datetime.datetime.utcnow().isoformat()
    # Build an initial record containing both the status and the search parameters.
    record = {
        "status": "processing",
        "requestedAt": requested_at,
        "results": None,
        "companyName": data.companyName,
        "registrationDateStart": data.registrationDateStart,
        "registrationDateEnd": data.registrationDateEnd
    }

    # Add the record using the entity service, providing the workflow
    # function that will process this record asynchronously before it is persisted.
    returned_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies_search",
        entity_version=ENTITY_VERSION,
        entity=record,
        workflow=process_companies_search  # Asynchronously update entity in place.
    )

    return jsonify({
        "requestId": returned_id,
        "status": "processing",
        "message": "Your request is being processed. Use the GET endpoint with your requestId to retrieve the results."
    })

# GET endpoint to retrieve the final search results.
@app.route('/companies/search/<job_id>', methods=['GET'])
async def get_search_results(job_id):
    job_record = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies_search",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job_record:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job_record)

# Entry point for the application.
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
-------------------------------------------------------------

Explanation of Changes:
1. The controller (endpoint) now only validates input and builds an initial record with the search parameters.
2. The enrichment and external API calls have been moved entirely into the workflow function (process_companies_search).
   • It fetches company data, filters active companies, enriches each result with LEI data, and updates the entity.
3. The workflow function modifies the given entity directly (adding attributes such as results, status, and processedAt).
4. The endpoint simply calls entity_service.add_item (now with the workflow function) and returns the assigned requestId.
5. There is no longer a need for explicitly launching an asynchronous background task from the endpoint since process_companies_search itself supports asynchronous operations.

This design “frees” the controller from excessive logic while keeping the enrichment and processing logic encapsulated within the workflow function, making the code more maintainable and robust.