Below is one complete updated refactoring that moves the external processing logic into the workflow function. Now the POST endpoint simply creates the initial job record (including the companyName needed for processing) and specifies the workflow function. The workflow function (process_companies) is defined as an asynchronous function that is given the entity (job data) as its only argument. Inside process_companies the external API call to fetch companies, filtering and LEI enrichment occur, and the entity’s state is updated directly (without calling any add/update/delete on the current entity). This approach “frees” the controller logic from fire‐and‐forget invocation and moves it into the workflow that is directly applied before persisting the entity.

Below is the complete code:

────────────────────────────
#!/usr/bin/env python3
import asyncio
import aiohttp
import datetime
import uuid

from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring

# Import and initialize external cyoda dependencies.
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)  # Enable Quart Schema integration

# Startup hook for external cyoda initialization.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Define dataclasses for request and response bodies.
@dataclass
class SearchRequest:
    companyName: str
    # TODO: Add additional optional filters if needed (registrationDateStart, registrationDateEnd, etc.).

@dataclass
class SearchResponse:
    jobId: str
    status: str
    message: str

@dataclass
class ResultsQuery:
    jobId: str

@dataclass
class ResultsResponse:
    jobId: str
    status: str
    requestedAt: str
    results: list = None
    error: str = None

async def fetch_lei(session: aiohttp.ClientSession, business_id: str):
    # TODO: Replace this mock with an actual call to an official LEI registry or reliable financial data source.
    await asyncio.sleep(0.1)
    if business_id and business_id[-1] in "13579":
        return f"MOCK_LEI_{business_id}"
    return None

async def process_companies(entity: dict) -> dict:
    """
    Workflow function to be applied to the 'companies' entity before persistence.
    This function is executed asynchronously and its returned state (the modified entity)
    will be persisted.
    
    In this implementation we:
      • Use the companyName stored in the entity (populated in the request) to call an external API.
      • Filter active companies.
      • Enrich each active company with LEI data.
      • Update the entity's state directly (by modifying its keys) to reflect the results.
      
    NOTE: Do not call entity_service.add/update/delete on this entity; simply change its state.
    """
    try:
        # We assume that companyName was added to the initial entity so that it can be used here.
        company_name = entity.get("companyName")
        if not company_name:
            entity["status"] = "failed"
            entity["error"] = "Missing companyName for processing"
            return entity

        async with aiohttp.ClientSession() as session:
            external_api_url = f"https://avoindata.prh.fi/opendata-ytj-api/v3/companies?name={company_name}"
            async with session.get(external_api_url) as resp:
                if resp.status == 200:
                    external_data = await resp.json()
                    companies = []
                    for company in external_data.get("results", []):
                        # TODO: Verify the field for business status. Here we assume it is "status" with value "active".
                        if company.get("status", "").lower() == "active":
                            companies.append(company)
                    # Enrich each active company with LEI data.
                    for company in companies:
                        lei = await fetch_lei(session, company.get("businessId", ""))
                        company["lei"] = lei if lei else "Not Available"
                    entity["results"] = companies
                    entity["status"] = "complete"
                else:
                    entity["status"] = "failed"
                    entity["error"] = f"External API error: status {resp.status}"
    except Exception as ex:
        entity["status"] = "failed"
        entity["error"] = str(ex)

    # For audit or debugging purposes we add a workflow timestamp.
    entity["workflowProcessedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    return entity

# POST endpoint:
# For POST endpoints, the decorator order should be route first then the validate decorators.
@app.route("/api/companies/search", methods=["POST"])
@validate_request(SearchRequest)
@validate_response(SearchResponse, 202)
async def search_company(data: SearchRequest):
    """
    POST endpoint to initiate a search.
    The business logic (external API calls, filtering, enrichment) has been moved to the workflow function:
    process_companies.
    
    The endpoint now only builds the initial job record. Notice that we include the companyName,
    which is required for the processing workflow.
    """
    if not data.companyName:
        return jsonify({"error": "companyName is required"}), 400

    requested_at = datetime.datetime.utcnow().isoformat() + "Z"
    # Initial record data that will be stored via external entity_service.
    # Include the companyName needed for processing.
    job_data = {
        "status": "processing",
        "requestedAt": requested_at,
        "companyName": data.companyName
    }
    # Add the new entry, specifying the workflow function.
    # The workflow function process_companies will be applied asynchronously before persistence.
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_data,  # the minimal job data (including companyName)
        workflow=process_companies  # The workflow function that replaces the fire-and-forget task.
    )
    return SearchResponse(jobId=job_id, status="processing", message="Search initiated"), 202

# GET endpoint:
# Note: For GET endpoints a known quart-schema issue requires the validation decorator first.
@validate_querystring(ResultsQuery)  # Workaround: always put validation first for GET.
@app.route("/api/companies/results", methods=["GET"])
async def get_results():
    """
    GET endpoint for retrieving processed search results.
    Expects jobId as a query parameter.
    """
    job_id = request.args.get("jobId")
    if not job_id:
        return jsonify({"error": "jobId is required"}), 400
    # Retrieve record via the external entity_service.
    job_data = await entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job_data:
        return jsonify({"error": "Job not found"}), 404

    response = ResultsResponse(
        jobId=job_id,
        status=job_data.get("status"),
        requestedAt=job_data.get("requestedAt", ""),
        results=job_data.get("results"),
        error=job_data.get("error")
    )
    return jsonify(response)

if __name__ == '__main__':
    # Run the Quart app with the given parameters.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

────────────────────────────
Observations:

1. The business logic that previously was performed inside a separate fire‐and‐forget task (process_entity)
   is now encapsulated in process_companies. This workflow function is invoked asynchronously by the
   entity_service.add_item call. By doing so, the controller (endpoint) remains lightweight and focuses
   solely on input validation and record creation.

2. The workflow function receives the job entity (which contains the companyName needed for the API call)
   and updates its state directly, rather than issuing any secondary persistence calls on the same entity.

3. By centralizing asynchronous processing in the workflow function, changes in business logic (e.g., registering
   new filters, enrichment steps, or error handling adjustments) will be easier to maintain without cluttering
   the controller code.

This refactoring meets the described requirements: it makes our code more robust, frees the controllers from
excessive logic, and utilizes the asynchronous workflow function as a direct alternative to fire‐and‐forget tasks.