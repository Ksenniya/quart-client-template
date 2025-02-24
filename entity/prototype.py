import asyncio
import uuid
import datetime
import aiohttp
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response

app = Quart(__name__)
QuartSchema(app)

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

# In-memory cache for query jobs
entity_jobs = {}

async def process_entity(job, payload_data):
    """
    Processes the incoming company query:
    - Retrieves data from the Finnish Companies Registry API.
    - Filters out inactive companies.
    - Enriches active companies with LEI data.
    """
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
    # Generate a unique query/job ID and store the initial job status.
    job_id = str(uuid.uuid4())
    job = {"status": "processing", "requestedAt": datetime.datetime.utcnow().isoformat() + "Z"}
    entity_jobs[job_id] = job

    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job, data))

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
    job = entity_jobs.get(job_id)
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