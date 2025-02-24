#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from dataclasses import dataclass
from quart import Quart, jsonify
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

# External API URLs
PRH_API_URL = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"  # Finnish Companies Registry API
LEI_API_URL = "https://lei.example.com/api/get"  # Placeholder for LEI lookup API

# Data classes for request/response validation
@dataclass
class CompanySearchRequest:
    companyName: str
    filters: dict = None  # Additional filtering options

@dataclass
class SearchResponse:
    requestId: str
    status: str
    message: str

async def fetch_companies(company_name: str, filters: dict):
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
                # Log non-200 responses if needed
                return []
        except Exception as e:
            # Prevent crash and log error details
            print(f"Error fetching companies: {e}")
            return []

async def fetch_lei(business_id: str):
    """
    Fetch the Legal Entity Identifier (LEI) for a given business ID.
    """
    params = {"businessId": business_id}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(LEI_API_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("lei", "Not Available")
                return "Not Available"
        except Exception as e:
            print(f"Error fetching LEI for {business_id}: {e}")
            return "Not Available"

async def process_entity(job_id: str, search_params: dict):
    """
    Process the search request.
    This function fetches companies, filters active ones,
    enriches them with LEI data, and updates the job entity.
    """
    company_name = search_params.get("companyName")
    filters = search_params.get("filters") or {}
    companies = await fetch_companies(company_name, filters)
    # Filter active companies with status 'active'
    active_companies = [comp for comp in companies if comp.get("status", "").lower() == "active"]

    enriched_results = []
    for company in active_companies:
        business_id = company.get("businessId")
        # Prevent processing if business_id is missing
        if not business_id:
            continue
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
    try:
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="companies_search_job",
            entity_version=ENTITY_VERSION,
            entity=update_data,
            meta={"id": job_id}
        )
    except Exception as ex:
        # In production, log the error result of update operation
        print(f"Error updating job {job_id}: {ex}")

async def process_companies_search_job(entity: dict):
    """
    Workflow function applied to the companies_search_job entity.
    Invoked asynchronously before persistence.
    It adds a workflow processing timestamp and fires off the processing task.
    Note: Do not use entity_service.add_item on the same entity_model here.
    """
    # Mark entity as processed by workflow
    entity["workflowProcessedAt"] = datetime.datetime.utcnow().isoformat()
    # Retrieve search parameters stored in the entity
    search_params = entity.get("searchParams", {})
    job_id = entity.get("id")
    if job_id and search_params:
        # Fire-and-forget asynchronous processing task
        asyncio.create_task(process_entity(job_id, search_params))
    else:
        print("Missing job id or search parameters in the entity.")
    # Return modified entity state for persistence
    return entity

@app.route("/companies/search", methods=["POST"])
@validate_request(CompanySearchRequest)  # Validate incoming request against CompanySearchRequest schema.
@validate_response(SearchResponse, 201)    # Validate outgoing response schema.
async def search_companies(data: CompanySearchRequest):
    """
    POST endpoint to trigger company search.
    It creates a job entity that stores parameters and delegates complex task processing
    to the workflow function (process_companies_search_job) invoked right before persistence.
    """
    requested_at = datetime.datetime.utcnow().isoformat()
    # Generate a unique job id
    job_id = str(uuid.uuid4())
    # Prepare job data with search parameters
    job_data = {
        "id": job_id,  # Unique job identifier for later retrieval
        "status": "processing",
        "requestedAt": requested_at,
        "searchParams": {
            "companyName": data.companyName,
            "filters": data.filters
        }
    }
    try:
        # Add job entity with workflow function that will modify the entity state asynchronously.
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="companies_search_job",
            entity_version=ENTITY_VERSION,
            entity=job_data,
            workflow=process_companies_search_job
        )
    except Exception as e:
        # Return error response if persisting job fails
        print(f"Error creating job: {e}")
        return jsonify({
            "requestId": job_id,
            "status": "failed",
            "message": "Unable to create a job for the search request."
        }), 500

    return jsonify({
        "requestId": job_id,
        "status": "processing",
        "message": "Your request is being processed. Retrieve results using GET /companies/result/<requestId>"
    }), 201

@app.route("/companies/result/<string:request_id>", methods=["GET"])
async def get_company_results(request_id: str):
    """
    GET endpoint to retrieve the search job results based on the provided job id.
    It returns status information and, if available, the enriched company results.
    """
    try:
        job = await entity_service.get_item(
            token=cyoda_token,
            entity_model="companies_search_job",
            entity_version=ENTITY_VERSION,
            technical_id=request_id
        )
    except Exception as e:
        print(f"Error retrieving job {request_id}: {e}")
        return jsonify({"error": "Unable to retrieve request status."}), 500

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