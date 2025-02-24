#!/usr/bin/env python3
import asyncio
import uuid
import datetime
import logging

import aiohttp
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring

from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Startup initialization
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Data classes for request/response validation
@dataclass
class CompanyRequest:
    companyName: str

@dataclass
class JobResponse:
    searchId: str
    status: str
    requestedAt: str

@dataclass
class QueryJob:
    searchId: str

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Asynchronous workflow function for "job" entity.
async def process_job(entity):
    # This workflow function is applied to the entity asynchronously before persistence.
    # Modify the entity state directly.
    if "technical_id" not in entity or not entity["technical_id"]:
        entity["technical_id"] = str(uuid.uuid4())
    entity["addedAt"] = datetime.datetime.utcnow().isoformat()
    # Start the enrichment processing asynchronously.
    company_name = entity.get("companyName")
    if company_name:
        # Fire-and-forget the external processing task.
        asyncio.create_task(process_entity(entity["technical_id"], {"companyName": company_name}))
    else:
        logger.error("Company name missing in entity workflow")
    return entity

async def process_entity(search_id, request_data):
    """
    Processing task:
      1. Call the Finnish Companies Registry API with the provided companyName.
      2. Filter out inactive companies.
      3. For each active company, call an external LEI lookup API.
      4. Update enriched results using the external entity_service.
    """
    results = []
    company_name = request_data.get("companyName")
    
    async with aiohttp.ClientSession() as session:
        # 1. Retrieve data from the Finnish Companies Registry API
        registry_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
        params = {"name": company_name}
        try:
            async with session.get(registry_url, params=params) as resp:
                if resp.status != 200:
                    logger.error("Finnish Registry API request failed with status %s", resp.status)
                    # Update job status with error details via external service
                    entity_service.update_item(
                        token=cyoda_token,
                        entity_model="job",
                        entity_version=ENTITY_VERSION,
                        entity={
                            "technical_id": search_id,
                            "status": "error",
                            "error": f"Registry API returned status {resp.status}"
                        },
                        meta={}
                    )
                    return
                registry_data = await resp.json()
        except Exception as e:
            logger.exception("Exception during Finnish Registry API request")
            entity_service.update_item(
                token=cyoda_token,
                entity_model="job",
                entity_version=ENTITY_VERSION,
                entity={
                    "technical_id": search_id,
                    "status": "error",
                    "error": str(e)
                },
                meta={}
            )
            return

        companies = registry_data.get("results", [])
        logger.info("Retrieved %d companies from registry", len(companies))

        # 2. Filter out inactive companies and retain only active companies
        active_companies = []
        for company in companies:
            if company.get("status", "").lower() == "active":
                active_companies.append(company)

        logger.info("Filtered to %d active companies", len(active_companies))

        # 3. For each active company, call an external LEI lookup service
        for company in active_companies:
            lei_service_url = "https://dummy-lei-lookup.com/api/lei"
            params = {"businessId": company.get("businessId")}
            try:
                async with session.get(lei_service_url, params=params) as lei_resp:
                    if lei_resp.status == 200:
                        lei_data = await lei_resp.json()
                        lei = lei_data.get("lei", "Not Available")
                    else:
                        lei = "Not Available"
                        logger.warning("LEI service returned status %s", lei_resp.status)
            except Exception as e:
                logger.exception("Exception during LEI lookup for company %s", company.get("businessId"))
                lei = "Not Available"

            enriched_company = {
                "companyName": company.get("companyName", "Unknown"),
                "businessId": company.get("businessId", "Unknown"),
                "companyType": company.get("companyType", "Unknown"),
                "registrationDate": company.get("registrationDate", "Unknown"),
                "status": company.get("status", "Unknown"),
                "lei": lei,
            }
            results.append(enriched_company)

        # 4. Update job record with results and mark processing as complete.
        entity_service.update_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            entity={
                "technical_id": search_id,
                "status": "done",
                "completedAt": datetime.datetime.utcnow().isoformat(),
                "results": results
            },
            meta={}
        )
        logger.info("Completed processing job %s", search_id)

# POST endpoint to trigger company enrichment.
@app.route("/api/company-enrichment", methods=["POST"])
@validate_request(CompanyRequest)  # Workaround: For POST, validation decorators go after the route decorator.
@validate_response(JobResponse, 202)
async def company_enrichment(data: CompanyRequest):
    """
    Expects JSON like: {"companyName": "Example Company"}.
    Returns a searchId for later retrieval.
    """
    requested_at = datetime.datetime.utcnow().isoformat()
    job_data = {
        "status": "processing",
        "requestedAt": requested_at,
        "results": None,
        "companyName": data.companyName,  # Include companyName for workflow processing.
    }
    # Add job item via external service with the workflow function.
    job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="job",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_data,  # the validated data object
        workflow=process_job  # Workflow function applied to the entity asynchronously before persistence.
    )
    return JobResponse(searchId=job_id, status="processing", requestedAt=requested_at), 202

# GET endpoint to retrieve enrichment results using a searchId query parameter.
@validate_querystring(QueryJob)  # Workaround: For GET, validation decorators go before the route decorator.
@app.route("/api/results", methods=["GET"])
async def results():
    """
    Example: GET /api/results?searchId=<job_uuid>
    """
    search_id = request.args.get("searchId")
    if not search_id:
        return jsonify({"error": "Missing searchId query parameter"}), 400

    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="job",
        entity_version=ENTITY_VERSION,
        technical_id=search_id
    )
    if not job:
        return jsonify({"error": "No job found with the provided searchId"}), 404

    return jsonify(job), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)