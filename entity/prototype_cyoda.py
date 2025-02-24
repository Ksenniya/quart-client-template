import asyncio
import uuid
import datetime
import aiohttp
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)

# Startup initialization
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Data models using dataclasses

@dataclass
class CompanyQuery:
    companyName: str
    # Using dict for additional search parameters; TODO: Refine this model when requirements are clearer.
    searchParameters: dict = None

@dataclass
class QueryResponse:
    queryId: str
    status: str
    message: str

async def process_entity(job_id: str, payload_data: CompanyQuery):
    """
    Processes the incoming company query:
    - Retrieves data from the Finnish Companies Registry API.
    - Filters out inactive companies.
    - Enriches active companies with LEI data.
    """
    # Retrieve current job state from the external service
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies_query",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if job is None:
        # In a real-world scenario, proper error logging/handling would be added here.
        return

    # Extract the company name and additional search parameters
    company_name = payload_data.companyName
    search_params = payload_data.searchParameters or {}

    # Construct the external API URL and parameters
    registry_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
    params = {"name": company_name}
    # TODO: Add additional search parameters from search_params if needed

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(registry_url, params=params) as resp:
                if resp.status == 200:
                    registry_data = await resp.json()
                else:
                    # TODO: Handle non-200 response appropriately
                    registry_data = {"results": []}
    except Exception as e:
        # TODO: Add proper error handling/logging here
        registry_data = {"results": []}

    # Filter out inactive companies.
    # Assuming that each company record includes a 'status' field indicating its activity ("Active"/"Inactive").
    companies = registry_data.get("results", [])
    active_companies = [comp for comp in companies if comp.get("status", "").lower() == "active"]

    # Enrich each active company with LEI data.
    for comp in active_companies:
        # TODO: Implement a real LEI lookup by querying official LEI registries.
        # Using a placeholder: if a company has a 'businessId', mock a LEI; otherwise "Not Available".
        comp["lei"] = "LEI-code-mock" if comp.get("businessId") else "Not Available"

    # Construct a simplified results list.
    job["results"] = [{
        "companyName": comp.get("name"),
        "businessId": comp.get("businessId"),
        "companyType": comp.get("companyType", "N/A"),
        "registrationDate": comp.get("registrationDate", "N/A"),
        "status": comp.get("status", "Inactive"),
        "lei": comp.get("lei")
    } for comp in active_companies]

    job["status"] = "completed"
    job["retrievedAt"] = datetime.datetime.utcnow().isoformat() + "Z"

    # Update the job in the external service
    entity_service.update_item(
        token=cyoda_token,
        entity_model="companies_query",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job,
        meta={}
    )

# NOTE: Due to an issue in quart-schema we must apply decorators as follows:
# For POST requests, use @app.route first, then @validate_request and @validate_response.
@app.route('/api/companies/query', methods=["POST"])
@validate_request(CompanyQuery)
@validate_response(QueryResponse, 201)
async def query_companies(data: CompanyQuery):
    """
    Initiates the company query process:
    - Receives JSON payload with companyName and optional searchParameters.
    - Fires off asynchronous processing for data retrieval, filtering, and enrichment.
    - Returns a queryId immediately.
    """
    # Create the initial job data with processing status and timestamp.
    job = {
        "status": "processing",
        "requestedAt": datetime.datetime.utcnow().isoformat() + "Z"
    }
    # Replace in-memory cache with external entity_service call to add the job.
    job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies_query",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job
    )

    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, data))

    return QueryResponse(
        queryId=job_id,
        status=job["status"],
        message="Data retrieval initiated."
    ), 201

# GET endpoint does not use request body; no validation decorators required.
@app.route('/api/companies/results/<job_id>', methods=["GET"])
async def get_results(job_id: str):
    """
    Retrieves the results of the company query processing using the queryId.
    Returns the queryId, current status, and enriched company data (if available).
    """
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies_query",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify({
        "queryId": job_id,
        "status": job.get("status"),
        "results": job.get("results", []),
        "retrievedAt": job.get("retrievedAt")
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)