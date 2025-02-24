#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response  # Workaround: For POST, decorators placed in order route then validate_request then validate_response
import aiohttp

from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# URL for external Finnish Companies Registry API (using v3 endpoint as provided)
PRH_API_URL = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
# Placeholder URL for LEI lookup (TODO: replace with official LEI registry API)
LEI_API_URL = "https://lei.example.com/api/get"

# Data classes for request/response validation
@dataclass
class CompanySearchRequest:
    companyName: str
    filters: dict = None  # TODO: refine structure of filters if needed

@dataclass
class SearchResponse:
    requestId: str
    status: str
    message: str

async def fetch_companies(company_name, filters):
    """
    Fetch companies from the Finnish Companies Registry API.
    """
    params = {"name": company_name}
    if filters:
        params.update(filters)
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(PRH_API_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("results", [])
                else:
                    return []
        except Exception as e:
            # TODO: Add proper error logging.
            print(f"Error fetching companies: {e}")
            return []

async def fetch_lei(business_id):
    """
    Fetch the Legal Entity Identifier (LEI) for a given business ID.
    """
    params = {"businessId": business_id}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(LEI_API_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('lei', "Not Available")
                else:
                    return "Not Available"
        except Exception as e:
            # TODO: Add proper error logging.
            print(f"Error fetching LEI for {business_id}: {e}")
            return "Not Available"

async def process_entity(job_id, search_params):
    """
    Process the search request: fetch, filter, enrich and update the results.
    """
    company_name = search_params.get("companyName")
    filters = search_params.get("filters") or {}
    companies = await fetch_companies(company_name, filters)
    active_companies = [comp for comp in companies if comp.get("status", "").lower() == "active"]

    enriched_results = []
    for company in active_companies:
        business_id = company.get("businessId")
        lei = await fetch_lei(business_id)
        enriched_company = {
            "companyName": company.get("companyName"),
            "businessId": business_id,
            "companyType": company.get("companyType"),
            "registrationDate": company.get("registrationDate"),
            "status": "Active",
            "lei": lei
        }
        enriched_results.append(enriched_company)

    update_data = {
        "status": "completed",
        "results": enriched_results,
        "completedAt": datetime.datetime.utcnow().isoformat()
    }
    await entity_service.update_item(
        token=cyoda_token,
        entity_model="companies_search_job",
        entity_version=ENTITY_VERSION,
        entity=update_data,
        meta={"id": job_id}
    )

async def process_companies_search_job(entity):
    # This workflow function is invoked asynchronously before persisting the entity.
    # Modify the entity state directly.
    entity["workflowProcessedAt"] = datetime.datetime.utcnow().isoformat()
    # Schedule the asynchronous enrichment processing as a fire-and-forget task.
    # It uses supplementary data stored within the entity.
    search_params = entity.get("searchParams", {})
    # The entity already has a unique identifier in 'id'
    job_id = entity.get("id")
    if job_id and search_params:
        asyncio.create_task(process_entity(job_id, search_params))
    return entity

@app.route("/companies/search", methods=["POST"])
@validate_request(CompanySearchRequest)  # For POST requests, decorators are placed after route decorator as a workaround for quart-schema issue.
@validate_response(SearchResponse, 201)
async def search_companies(data: CompanySearchRequest):
    """
    POST endpoint to trigger the company data retrieval, filtering, enrichment and asynchronous processing.
    The search parameters are stored with the job and processed via the workflow function.
    """
    requested_at = datetime.datetime.utcnow().isoformat()
    # Pre-generate a unique job id and include the search parameters to be used later by the workflow.
    job_id = str(uuid.uuid4())
    job_data = {
        "id": job_id,  # Unique identifier for this job
        "status": "processing",
        "requestedAt": requested_at,
        "searchParams": {"companyName": data.companyName, "filters": data.filters}
    }
    # The workflow function 'process_companies_search_job' will be invoked before persisting the entity.
    await entity_service.add_item(
        token=cyoda_token,
        entity_model="companies_search_job",
        entity_version=ENTITY_VERSION,
        entity=job_data,
        workflow=process_companies_search_job
    )

    return jsonify({
        "requestId": job_id,
        "status": "processing",
        "message": "Your request is being processed. Retrieve results using GET /companies/result/<requestId>"
    }), 201

@app.route("/companies/result/<string:request_id>", methods=["GET"])
async def get_company_results(request_id):
    """
    GET endpoint to retrieve the enriched company data by request ID.
    """
    job = await entity_service.get_item(
        token=cyoda_token,
        entity_model="companies_search_job",
        entity_version=ENTITY_VERSION,
        technical_id=request_id
    )
    if not job:
        return jsonify({"error": "Request ID not found"}), 404

    if job.get("status") != "completed":
        return jsonify({
            "requestId": request_id,
            "status": job.get("status"),
            "message": "Results are not yet ready. Please try again later."
        }), 202

    return jsonify({
        "requestId": request_id,
        "results": job.get("results", [])
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)