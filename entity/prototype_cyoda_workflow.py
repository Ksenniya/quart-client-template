Below is one complete updated code example. In this version we define an asynchronous workflow function (process_companies) that will be applied to the “companies” entity prior to persistence. In the search_company endpoint the call to entity_service.add_item now provides the workflow function as an additional parameter. (Note that further workflow logic can be added as necessary; here we keep it simple by, for example, appending a timestamp to the entity.) 

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

# Define dataclasses for request and response bodies
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

async def process_entity(job_id: str, payload: dict):
    """Process the search payload: fetch companies, filter active ones,
       and enrich each with LEI data.
       Updates the record in the external entity_service using update_item.
    """
    try:
        async with aiohttp.ClientSession() as session:
            company_name = payload.get("companyName")
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
                    # Build update payload for a successful processing.
                    update_data = {
                        "results": companies,
                        "status": "complete"
                    }
                else:
                    update_data = {
                        "status": "failed",
                        "error": f"External API error: status {resp.status}"
                    }
    except Exception as ex:
        update_data = {
            "status": "failed",
            "error": str(ex)
        }
    # Update our record via external entity_service.
    await entity_service.update_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        entity=update_data,
        meta={"technical_id": job_id}
    )

async def process_companies(entity: dict) -> dict:
    """
    Workflow function to be applied on an entity (of entity_model "companies")
    before its persistence. This function can be used to enrich or validate
    the entity, for example adding a timestamp to indicate that workflow processing
    was applied. Note: This function will be executed asynchronously as part of the add_item process.
    """
    # Add a timestamp marking when the workflow was applied.
    entity["workflowProcessedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    # Additional processing logic may be added here.
    return entity

# POST endpoint:
# For POST endpoints, the route decorator must be first followed by validate_request and validate_response.
@app.route("/api/companies/search", methods=["POST"])
@validate_request(SearchRequest)
@validate_response(SearchResponse, 202)
async def search_company(data: SearchRequest):
    """
    POST endpoint to initiate a search.
    This endpoint performs external API calls and processing in a fire-and-forget task.
    Request JSON should include:
      - companyName (required)
      - optional filters
    """
    if not data.companyName:
        return jsonify({"error": "companyName is required"}), 400

    requested_at = datetime.datetime.utcnow().isoformat() + "Z"
    # Initial record data that will be stored via external entity_service.
    job_data = {
        "status": "processing",
        "requestedAt": requested_at
    }
    # Add the new entry, passing the workflow function as an additional parameter. The workflow function
    # (process_companies) will be applied to job_data before it gets persisted.
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_data,  # the validated data object
        workflow=process_companies  # Workflow function applied asynchronously before persistence.
    )
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, data.__dict__))
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

Notes:
1. All local in‑memory variables have been replaced by calls to entity_service.add_item, get_item, and update_item.
2. The unique job id (returned by add_item) is now included in the response so that users can query their results later.
3. The business logic – including external API calls, filtering, and LEI enrichment – remains intact.
4. The workflow function (process_companies) is provided to add_item so that extra work on the entity (such as adding a processing timestamp) is performed before the entity is persisted.
5. If additional methods such as delete_item or get_items_by_condition become necessary in the future, you can similarly replace the corresponding in‑memory cache functionality.

This completes the updated refactoring as specified.