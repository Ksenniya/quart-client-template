Below is one acceptable refactored version of the prototype file. In this version all reads and writes to the local in‑memory “jobs” cache have been replaced by calls to the external entity_service (using only the allowed functions). In addition, the extra startup code is added and ENTITY_VERSION is imported from common.config.config. (In the code, we use the same "companies" string as the entity model.) You should verify that the external service’s update_item call can be made to use the job’s technical id (here we are passing it in meta). If needed further adjustments could be made.

-------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
import aiohttp
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring

# NEW: Import the ENTITY_VERSION constant and the cyoda startup/init functions
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Add startup hook to initialize cyoda
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)


# Data models for validation (only primitives as per guidelines)
@dataclass
class EnrichRequest:
    companyName: str
    # Optional filters; additional fields added as needed
    location: str = None
    businessId: str = None
    registrationDateStart: str = None
    registrationDateEnd: str = None

@dataclass
class EnrichResponse:
    requestId: str
    status: str
    message: str
    # Data field is dynamic; skipping detailed validation (TODO if needed)
    data: str = None

@dataclass
class EnrichQuery:
    requestId: str


async def fetch_company_data(company_name: str, filters: dict) -> dict:
    """
    Query the Finnish Companies Registry API.
    TODO: Adjust request parameters and response parsing based on the actual API contract.
    """
    url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
    # Build query parameters: mandatory company name with any provided filters
    params = {"name": company_name}
    params.update(filters)
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                # TODO: Adapt parsing based on the actual API response structure.
                return data
            else:
                # TODO: Improve error handling/logging
                return {"companies": []}


async def fetch_lei(company: dict) -> str:
    """
    Fetch the Legal Entity Identifier (LEI) for the given company.
    This is currently a mock implementation.
    TODO: Replace with a real external call to an official LEI registry or a reliable data source.
    """
    await asyncio.sleep(0.1)  # Simulate network delay
    if company.get("companyName"):
        return "MOCK_LEI_123456789"
    return "Not Available"


async def process_entity(job_id: str, criteria: dict):
    """
    Process the entity by retrieving, filtering, and enriching company data.
    Once complete, update the job record via entity_service.
    """
    company_name = criteria.get("companyName")
    # Build filters from available keys (excluding companyName)
    filters = {k: v for k, v in criteria.items() if k != "companyName" and v is not None}
    # Retrieve data from the Finnish Companies Registry
    companies_response = await fetch_company_data(company_name, filters)
    companies = companies_response.get("companies", [])
    
    # Filter out inactive companies; assuming "status" indicates business status.
    active_companies = [comp for comp in companies if comp.get("status", "").lower() == "active"]
    
    enriched_companies = []
    for company in active_companies:
        lei = await fetch_lei(company)
        enriched_company = {
            "companyName": company.get("companyName"),
            "businessId": company.get("businessId"),
            "companyType": company.get("companyForm"),  # Mapping companyForm as companyType
            "registrationDate": company.get("registrationDate"),
            "status": company.get("status"),
            "lei": lei if lei else "Not Available"
        }
        enriched_companies.append(enriched_company)
    
    # Prepare update payload with enriched data and updated status.
    job_update = {
        "status": "completed",
        "requestedAt": datetime.datetime.utcnow().isoformat(),
        "data": enriched_companies,
        # Including the technical id in the entity data for reference.
        "technicalId": job_id
    }
    # Replace updating the local cache with an external update
    entity_service.update_item(
        token=cyoda_token,
        entity_model="companies",  # using "companies" as the entity name
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_update,
        meta={"technical_id": job_id}
    )


# POST endpoint: route decorator comes first, then validate_request, then validate_response.
@app.route("/companies/enrich", methods=["POST"])
@validate_request(EnrichRequest)  # For POST endpoints, validation comes after route decorator.
@validate_response(EnrichResponse, 200)
async def enrich_companies(data: EnrichRequest):
    """
    Accepts search criteria and triggers external API calls for enrichment.
    Returns immediately with a job ID while processing occurs in the background.
    """
    # Create the initial job payload and store it via the external service.
    job_data = {
        "status": "processing",
        "requestedAt": datetime.datetime.utcnow().isoformat()
    }
    # Instead of storing to a local dict, add the job to external persistence.
    job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",  # using "companies" as the entity model
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_data  # the validated object with metadata
    )
    # Fire-and-forget processing task.
    asyncio.create_task(process_entity(job_id, data.__dict__))
    
    response = {
        "requestId": job_id,
        "status": "processing",
        "message": "Job started",
        "data": ""  # Data will be available via GET /companies/results.
    }
    return jsonify(response)


# GET endpoint: validation decorator comes first (workaround for GET validation issue)
@validate_querystring(EnrichQuery)  # For GET, this decorator is placed first.
@app.route("/companies/results", methods=["GET"])
async def get_results():
    """
    Retrieves enriched company results of a previously initiated job using the requestId.
    (Access parameters via standard request.args since GET requests cannot have a body.)
    """
    job_id = request.args.get("requestId")
    if not job_id:
        return jsonify({"error": "Missing requestId parameter"}), 400
    
    # Instead of reading from a local cache, retrieve the job from the external service.
    result = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not result:
        return jsonify({"error": "Job not found"}), 404
    
    response = {
        "requestId": job_id,
        "status": result.get("status"),
        "message": "Job completed" if result.get("status") == "completed" else "Job processing",
        "data": result.get("data", [])
    }
    return jsonify(response)


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
-------------------------------------------------

Notes:
1. All local cache actions (using the “jobs” dictionary) have been removed in favor of calling entity_service.add_item, update_item, and get_item.
2. When a new enrichment job is started, its returned id (job_id) is added to the response so clients may later query for the job result with GET /companies/results?requestId=<job_id>.
3. If more external functions had been necessary then – per instructions – we would have skipped them. In this solution only the allowed functions are used.
4. The business logic (ingesting request data, calling external APIs, filtering, enriching, etc.) has been preserved.

This refactoring should meet the integration requirements with the external entity_service.