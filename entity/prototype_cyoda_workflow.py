Below is one complete revised example. In this version the add_item call now passes a workflow function (named process_companies) so that the job “entity” is transformed asynchronously before it is persisted. Notice that process_companies (which takes the entity data as its only argument) now performs the enrichment logic (calling external APIs and updating the entity’s state) and returns the updated entity. Also note that because updating entities of the same model inside the workflow is disallowed (in order to avoid infinite recursion), all persistence of the changed job is handled automatically by entity_service after the workflow returns. (Any additional operations on other entity models are still permitted.) 

Below is the complete code (for example, in entity/prototype_cyoda.py):

--------------------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from dataclasses import dataclass

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring

# Import the external entity_service and cyoda_token along with the configuration constant
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

# -----------------------------
# Startup: Initialize the external cyoda service at application start‐up
# -----------------------------
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# -----------------------------
# Dataclasses for request validation
# -----------------------------
@dataclass
class CompanySearchReq:
    name: str
    page: int = 1

@dataclass
class JobQuery:
    requestId: str

# -----------------------------
# Workflow function: process_companies
#
# This asynchronous function will be applied to the job (entity) before it is persisted.
# It reads the search criteria saved inside the entity, calls the external API,
# and enriches the job by adding the search results. Notice that it does not
# update the entity via the same service (which would cause recursion); instead,
# it merely modifies the entity that will be saved.
# -----------------------------
async def process_companies(entity: dict) -> dict:
    try:
        # Retrieve search criteria from the entity; note that job_data["criteria"] is expected to be a dict.
        criteria = entity.get("criteria", {})
        if not criteria.get("name"):
            entity["status"] = "failed"
            entity["error"] = "Company name is required"
            return entity

        import aiohttp
        async with aiohttp.ClientSession() as session:
            prh_api_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
            params = {"name": criteria.get("name"), "page": criteria.get("page", 1)}
            async with session.get(prh_api_url, params=params) as resp:
                if resp.status != 200:
                    # In production, handle errors more gracefully.
                    prh_data = {"results": []}
                else:
                    prh_data = await resp.json()

            # Keep only companies that are “active”
            active_companies = [
                company for company in prh_data.get("results", [])
                if company.get("status", "").lower() == "active"
            ]

            # Enrich each active company with additional LEI data.
            enriched_results = []
            for company in active_companies:
                lei = await fetch_lei_for_company(company, session)
                enriched_company = {
                    "companyName": company.get("name", "N/A"),
                    "businessId": company.get("businessId", "N/A"),
                    "companyType": company.get("companyType", "N/A"),
                    "registrationDate": company.get("registrationDate", "N/A"),
                    "status": company.get("status", "N/A"),
                    "LEI": lei,
                }
                enriched_results.append(enriched_company)

            # Update the entity with the enrichment results.
            entity["results"] = enriched_results
            entity["completed"] = True
            entity["status"] = "completed"

    except Exception as e:
        # On error, mark the job as failed and record the error.
        entity["status"] = "failed"
        entity["error"] = str(e)

    return entity

# -----------------------------
# Async function to fetch LEI data (mock implementation)
# -----------------------------
async def fetch_lei_for_company(company: dict, session) -> str:
    # In a real system this would call an external LEI API.
    await asyncio.sleep(0.1)  # Simulate network delay.
    return "Not Available"  # Placeholder value.

# -----------------------------
# POST endpoint to initiate company search and enrichment.
#
# The workflow function is passed to entity_service.add_item.
# The service will call process_companies (asynchronously) on the job entity before persisting.
# -----------------------------
@app.route('/api/v1/companies/search', methods=['POST'])
@validate_request(CompanySearchReq)
@validate_response(dict, 200)
async def search_companies(data: CompanySearchReq):
    # Build the initial job payload containing the search criteria.
    requested_at = datetime.datetime.utcnow().isoformat()
    job_data = {
        "status": "processing",
        "requestedAt": requested_at,
        "criteria": data.__dict__
    }

    # Create the job via entity_service.add_item passing the workflow function.
    created_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        entity=job_data,
        workflow=process_companies  # The workflow function to process this entity before it is persisted.
    )

    # Immediately return a response including the job’s ID.
    return jsonify({
        "requestId": created_id,
        "status": "processing",
        "message": "Search initiated. Please poll the GET endpoint for results."
    })

# -----------------------------
# GET endpoint to retrieve the search results.
#
# It uses the external entity_service.get_item method to retrieve the processed job.
# -----------------------------
@validate_querystring(JobQuery)
@app.route('/api/v1/companies/results', methods=['GET'])
async def get_results():
    requestId = request.args.get("requestId")
    if not requestId:
        return jsonify({"error": "requestId parameter is required"}), 400

    # Retrieve the job using the external service.
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=requestId
    )
    if not job:
        return jsonify({"error": "Job not found"}), 404

    # Return the job details.
    return jsonify({
        "requestId": requestId,
        "results": job.get("results", []),
        "completed": job.get("completed", False),
        "status": job.get("status")
    })

# -----------------------------
# Application entry point.
# -----------------------------
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
--------------------------------------------------------------

Explanation of the key changes:

1. In the POST endpoint (/api/v1/companies/search) the call to entity_service.add_item now includes an extra parameter – workflow=process_companies. This signals that before the job is persisted the entity_service should call process_companies with the job’s data.
2. The new workflow function process_companies takes the unpersisted job entity, reads the search criteria, calls the external PRH API (and fetch_lei_for_company for simulated LEI lookup), then enriches the entity with the results (or with an error in case of failure). The modified entity is then returned so that the external service will persist it.
3. Because the workflow function is applied “before persistence”, there is no need for the explicit asyncio.create_task or a subsequent update via update_item from within the endpoint.
4. The GET endpoint (/api/v1/companies/results) remains unchanged – it simply retrieves the already enriched job from the entity_service.

This revised code fully incorporates the new workflow function mechanism for add_item.