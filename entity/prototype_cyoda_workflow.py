#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring  # Issue workaround: For POST, validation decorators come after route decorator; for GET, they must be placed first.
import aiohttp

from common.config.config import ENTITY_VERSION  # always use this constant
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)  # Integrate QuartSchema

# Workflow function for the "company_job" entity.
# It is applied to the entity before it is persisted.
def process_company_job(entity):
    # For example, add a timestamp indicating when the workflow was applied.
    entity["workflow_processed_at"] = datetime.datetime.utcnow().isoformat()
    return entity

# Startup initialization for external service.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Data classes for validation
@dataclass
class SearchRequest:
    company_name: str
    registration_date_start: str = None
    registration_date_end: str = None
    businessId: str = None
    companyForm: str = None
    # TODO: Add other filters as necessary

@dataclass
class SearchResponse:
    search_id: str
    status: str

# In the refactored version, we remove the in‐memory cache and rely on entity_service.
# The entity_model used for job data will be "company_job".

@app.route("/companies/search", methods=["POST"])
@validate_request(SearchRequest)  # For POST, validation decorators come after route decorator (workaround for quart-schema issue)
@validate_response(SearchResponse, 200)
async def search_companies(data: SearchRequest):
    try:
        # Use validated data from SearchRequest dataclass
        if not data.company_name:
            return jsonify({"error": "company_name is required"}), 400

        job_id = str(uuid.uuid4())
        requested_at = datetime.datetime.utcnow().isoformat()
        job_data = {"technical_id": job_id, "status": "processing", "requestedAt": requested_at, "results": None}

        # Store job record using the external entity_service with workflow function applied.
        job_id = entity_service.add_item(
            token=cyoda_token,
            entity_model="company_job",
            entity_version=ENTITY_VERSION,
            entity=job_data,
            workflow=process_company_job  # Workflow function applied asynchronously before persistence.
        )

        # Fire and forget processing task.
        asyncio.create_task(process_entity(job_id, data))
        return {"search_id": job_id, "status": "processing"}
    except Exception as e:
        # TODO: Enhance error handling as needed.
        return jsonify({"error": str(e)}), 500

@app.route("/companies/search/<job_id>", methods=["GET"])
async def get_search_results(job_id: str):
    # Retrieve job record using the external service.
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="company_job",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        return jsonify({"error": "Job ID not found"}), 404
    if job.get("status") != "completed":
        return jsonify({"search_id": job_id, "status": job.get("status")})
    return jsonify({"search_id": job_id, "status": job.get("status"), "results": job.get("results")})

async def process_entity(job_id: str, search_data: SearchRequest):
    """
    Core business logic:
    - Call Finnish Companies Registry API (PRH API)
    - Filter out inactive companies
    - For each active company, retrieve LEI data
    - Save enriched results via the external entity_service
    """
    results = []
    try:
        async with aiohttp.ClientSession() as session:
            # Form external API URL using the company_name filter.
            PRH_API_BASE_URL = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
            params = {"name": search_data.company_name}
            # TODO: Add additional filters (registration_date_start, registration_date_end, etc.) if provided.
            async with session.get(PRH_API_BASE_URL, params=params) as response:
                if response.status != 200:
                    # Update job as failed if the external API call fails.
                    job = entity_service.get_item(
                        token=cyoda_token,
                        entity_model="company_job",
                        entity_version=ENTITY_VERSION,
                        technical_id=job_id
                    )
                    if job:
                        job["status"] = "failed"
                        entity_service.update_item(
                            token=cyoda_token,
                            entity_model="company_job",
                            entity_version=ENTITY_VERSION,
                            entity=job,
                            meta={}
                        )
                    return
                prh_data = await response.json()
                # TODO: Adjust according to the actual PRH API response structure.
                companies = prh_data.get("results", [])
                for company in companies:
                    # Process only companies with active status.
                    if company.get("status", "").lower() != "active":
                        continue

                    enriched_company = {}
                    enriched_company["company_name"] = company.get("name", "N/A")
                    enriched_company["business_id"] = company.get("businessId", "N/A")
                    enriched_company["company_type"] = company.get("companyForm", "N/A")
                    enriched_company["registration_date"] = company.get("registrationDate", "N/A")
                    enriched_company["status"] = company.get("status", "N/A")

                    lei = await fetch_lei(session, enriched_company)
                    enriched_company["lei"] = lei if lei else "Not Available"
                    results.append(enriched_company)

        # After processing, update the job record with the results.
        job = entity_service.get_item(
            token=cyoda_token,
            entity_model="company_job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
        if job:
            job["status"] = "completed"
            job["results"] = results
            entity_service.update_item(
                token=cyoda_token,
                entity_model="company_job",
                entity_version=ENTITY_VERSION,
                entity=job,
                meta={}
            )

    except Exception as e:
        # Update job record with error information.
        job = entity_service.get_item(
            token=cyoda_token,
            entity_model="company_job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
        if job:
            job["status"] = "failed"
            job["results"] = {"error": str(e)}
            entity_service.update_item(
                token=cyoda_token,
                entity_model="company_job",
                entity_version=ENTITY_VERSION,
                entity=job,
                meta={}
            )

async def fetch_lei(session: aiohttp.ClientSession, company: dict) -> str:
    """
    Attempts to retrieve LEI for a given company.
    Uses placeholder logic until actual LEI service details are provided.
    TODO: Replace with actual implementation when LEI service details are available.
    """
    try:
        business_id = company.get("business_id", "")
        if business_id and business_id[-1] in "02468":
            # TODO: Perform an actual async call to the LEI service when available.
            return "529900T8BM49AURSDO55"  # Mocked LEI value
        else:
            return None
    except Exception as e:
        # TODO: Handle errors in external LEI fetch properly.
        return None

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)