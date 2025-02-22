Below is one complete refactored version that “frees” the controller from any asynchronous processing logic. Instead of the POST endpoint launching a separate background task (fire‐and‐forget), we now pass all the asynchronous processing logic into the workflow function process_companies_workflow. That function receives the job entity (which in this example we enhance to also include the original request payload) and then calls the external APIs, filters results, enriches each company with LEI data, and finally updates the entity’s state (for example, setting status to completed and adding the processed results). Since entity_service.add_item will invoke the passed workflow function (and await it if needed), any asynchronous code may be executed there safely. Note that the workflow function must not call entity_service.add_item/update/delete on the same entity model – instead, it simply modifies the given entity object.

Below is the complete code:

------------------------------------------------------------
#!/usr/bin/env python3
"""
prototype.py

A working prototype for the Finnish Companies Data Retrieval and Enrichment Application.
External calls use aiohttp.ClientSession. Persistence is now managed via an external service,
entity_service. The add_item function now accepts an extra asynchronous workflow function.
This workflow function is applied on the newly created job entity (which now also contains the original
payload) right before persistence. There, all the asynchronous processing (external API calls, filtering,
enrichment, etc.) will be performed, and any modifications to the entity will be persisted.
Any incomplete requirements (such as the LEI lookup logic) are marked with TODO comments.
"""

import asyncio
import datetime
from dataclasses import dataclass
from typing import Optional

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring
import aiohttp

# Import external service, token, and constant.
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Enable Quart Schemas

# Startup hook to initialize cyoda service.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# ----- Dataclass models for request/response validation -----

@dataclass
class CompanyFilters:
    location: Optional[str] = None
    companyForm: Optional[str] = None
    page: Optional[int] = None

@dataclass
class CompanyRequest:
    companyName: str
    filters: Optional[CompanyFilters] = None

@dataclass
class CompanyJobResponse:
    jobId: str
    status: str

async def get_lei_for_company(company: dict) -> Optional[str]:
    """
    Placeholder for LEI lookup.
    TODO: Replace with an actual HTTP request to a reliable LEI lookup service.
          For now, this function simulates a delay and returns a dummy LEI for companies
          whose name starts with the letter 'A' (case-insensitive).
    """
    await asyncio.sleep(0.1)
    if company.get("name", "").lower().startswith("a"):
        return "DUMMY-LEI-12345"
    return None

async def process_companies_workflow(entity: dict) -> dict:
    """
    Workflow function applied asynchronously to the job entity before it is persisted.
    In this implementation:
      1. It reads the original payload from the job entity (stored on key 'payload').
      2. It calls the external Finnish Companies Registry API.
      3. It applies any filters and then processes the companies:
           - Filters out non-active companies.
           - Enriches active companies with LEI lookup.
      4. It then updates the current entity state by adding a status ("completed")
         and saving the enriched results.
    IMPORTANT: This function modifies the entity in place. Do not call any entity_service functions here.
    """
    # Retrieve the payload that was stored in the entity.
    payload = entity.get("payload", {})
    company_name = payload.get("companyName")
    filters = payload.get("filters", {})

    # Step 1: Prepare request to the Finnish Companies Registry API.
    prh_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
    params = {"name": company_name}
    if filters:
        if filters.get("location"):
            params["location"] = filters["location"]
        if filters.get("companyForm"):
            params["companyForm"] = filters["companyForm"]
        if filters.get("page"):
            params["page"] = filters["page"]

    # Step 2: Call the external API.
    companies_data = {}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(prh_url, params=params) as response:
                if response.status == 200:
                    companies_data = await response.json()
                else:
                    # TODO: Handle non-200 responses as needed.
                    companies_data = {}
        except Exception as e:
            # TODO: Improve error handling (e.g., logging) here.
            companies_data = {}

    # Assume companies_data contains a list of companies under key 'results'.
    companies = companies_data.get("results", [])

    # Step 3: Filter out inactive companies.
    # For this prototype, we assume a field "status" where "active" indicates an active company.
    active_companies = [
        company for company in companies 
        if company.get("status", "").lower() == "active"
    ]

    # Step 4: Enrich each active company with LEI information.
    enriched_results = []
    for company in active_companies:
        lei = await get_lei_for_company(company)
        enriched_results.append({
            "companyName": company.get("name", "Unknown"),
            "businessId": company.get("businessId", "Unknown"),
            "companyType": company.get("companyType", "Unknown"),
            "registrationDate": company.get("registrationDate", "Unknown"),
            "status": company.get("status", "Unknown"),
            "LEI": lei if lei else "Not Available"
        })

    # Step 5: Modify the current entity with new state details.
    entity["status"] = "completed"
    entity["completedAt"] = datetime.datetime.utcnow().isoformat()
    entity["result"] = enriched_results

    # Optional: add a flag to indicate that the workflow has been applied.
    entity["workflowApplied"] = True

    return entity

# --- POST endpoint to trigger processing ---
@app.route("/companies", methods=["POST"])
@validate_request(CompanyRequest)  # For POST, the route is defined first, then validation.
@validate_response(CompanyJobResponse, 201)
async def post_companies(data: CompanyRequest):
    """
    POST endpoint to trigger data retrieval, filtering, and enrichment.
    Accepts JSON with required field 'companyName' and optional 'filters'.
    Returns a jobId for retrieving results later.
    
    In this version the minimal job data (with a copy of the payload) is stored, and the
    asynchronous processing is performed in process_companies_workflow (called by entity_service.add_item).
    """
    # Construct the payload based on validated request.
    payload = {
        "companyName": data.companyName,
        "filters": {
            "location": data.filters.location if data.filters else None,
            "companyForm": data.filters.companyForm if data.filters else None,
            "page": data.filters.page if data.filters else None
        } if data.filters else {}
    }
    # Include creation details along with the payload.
    job_data = {
        "status": "processing",
        "requestedAt": datetime.datetime.utcnow().isoformat(),
        "payload": payload  # Store the payload so the workflow can use it.
    }
    # Call add_item with process_companies_workflow as the workflow function.
    # The workflow function will be invoked asynchronously before the job is finally persisted.
    job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_data,  # the initial job data that includes the request payload.
        workflow=process_companies_workflow  # The workflow function performs all async processing.
    )
    
    # The controller now only creates the job record, freeing it from any additional logic.
    response = CompanyJobResponse(jobId=job_id, status="processing")
    return jsonify(response.__dict__), 201

# --- GET endpoint to retrieve job results ---
@app.route("/companies/<job_id>", methods=["GET"])
async def get_companies(job_id):
    """
    GET endpoint to retrieve processing results using a jobId.
    No validation of the job_id is performed as it is taken from the path variable.
    """
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(job)

# Optional extra GET endpoint (for example, retrieving LEI for one of the companies).
@validate_querystring(CompanyRequest)  # Workaround for GET query parameter validation.
@app.route("/companies/<string:job_id>/lei", methods=["GET"])
async def get_company_lei(job_id):
    """
    GET endpoint to retrieve LEI information for a company within a job.
    NOTE: This endpoint is illustrative. In a robust solution, you might provide more advanced query options.
    """
    # Traditional access via request args.
    dummy_param = request.args.get('dummy')  # TODO: Replace with actual parameter if needed.
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        return jsonify({"error": "Job not found"}), 404
    # For demonstration, return the LEI of the first enriched company.
    result = job.get("result", [])
    lei_info = result[0].get("LEI") if result else "Not Available"
    return jsonify({"jobId": job_id, "LEI": lei_info})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
------------------------------------------------------------

Explanation of key changes:

1. The POST endpoint now builds a job entity that contains both the status and a copy of the request payload (under the key "payload"). This makes the extra data needed for processing available to the workflow.
2. The asynchronous processing—including external API invocation, filtering, enrichment, and state update—is moved entirely to the process_companies_workflow function. This function receives the job entity, modifies it asynchronously, and its returned state is then persisted.
3. Fire-and-forget logic has been removed from the controller. Now, the controller simply calls entity_service.add_item with the workflow function.
4. The workflow function does not call any entity_service.add_item/update/delete for the current entity; it only modifies the local state (e.g. entity["status"], entity["result"]) directly, which is then persisted by entity_service following the workflow invocation.

This approach makes your controllers lean and robust while centralizing all asynchronous processing logic in the dedicated workflow function.