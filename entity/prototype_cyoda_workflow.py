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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Startup initialization
@app.before_serving
async def startup():
    try:
        await init_cyoda(cyoda_token)
        logger.info("CYODA initialization completed.")
    except Exception as e:
        logger.exception("Failed to initialize CYODA: %s", e)

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

################################################################################
# Workflow function for "job" entity.
# This function is applied asynchronously before the entity is persisted.
# It modifies the entity state, assigns a unique technical_id (if missing),
# sets a creation timestamp, and triggers further asynchronous enrichment.
################################################################################
async def process_job(entity):
    try:
        # Ensure a technical_id is present; do not reassign if already exists.
        if "technical_id" not in entity or not entity["technical_id"]:
            entity["technical_id"] = str(uuid.uuid4())
        # Add a timestamp for when the entity was added.
        entity["addedAt"] = datetime.datetime.utcnow().isoformat()
        # Validate required field for processing.
        company_name = entity.get("companyName")
        if not company_name:
            logger.error("Missing companyName in the job entity; skipping enrichment process.")
            entity["status"] = "error"
            entity["error"] = "Missing companyName"
            return entity
        # Immediately mark the status as processing.
        entity["status"] = "processing"
        # Launch asynchronous enrichment processing as a fire-and-forget task.
        asyncio.create_task(process_entity(entity["technical_id"], {"companyName": company_name}))
    except Exception as e:
        logger.exception("Error in process_job workflow: %s", e)
        entity["status"] = "error"
        entity["error"] = str(e)
    return entity

################################################################################
# Asynchronous processing function to enrich the job entity.
# It calls external APIs to fetch company registry data and LEI lookup.
# On failure, it updates the job status with error details.
# The update_item call here is for a different phase (updating job results)
# and is safe because it targets an already persisted entity.
################################################################################
async def process_entity(search_id, request_data):
    results = []
    company_name = request_data.get("companyName")
    async with aiohttp.ClientSession() as session:
        # Call Finnish Companies Registry API
        registry_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
        params = {"name": company_name}
        try:
            async with session.get(registry_url, params=params) as resp:
                if resp.status != 200:
                    error_msg = f"Registry API returned status {resp.status}"
                    logger.error(error_msg)
                    entity_service.update_item(
                        token=cyoda_token,
                        entity_model="job",
                        entity_version=ENTITY_VERSION,
                        entity={
                            "technical_id": search_id,
                            "status": "error",
                            "error": error_msg
                        },
                        meta={}
                    )
                    return
                registry_data = await resp.json()
        except Exception as e:
            logger.exception("Exception calling Finnish Registry API")
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
        logger.info("Retrieved %d companies for '%s'", len(companies), company_name)
        
        # Filter only active companies.
        active_companies = [company for company in companies if company.get("status", "").lower() == "active"]
        logger.info("Found %d active companies", len(active_companies))
        
        # For every active company, perform LEI lookup.
        for company in active_companies:
            lei = "Not Available"
            lei_service_url = "https://dummy-lei-lookup.com/api/lei"
            lookup_params = {"businessId": company.get("businessId")}
            try:
                async with session.get(lei_service_url, params=lookup_params) as lei_resp:
                    if lei_resp.status == 200:
                        lei_data = await lei_resp.json()
                        lei = lei_data.get("lei", lei)
                    else:
                        logger.warning("LEI lookup returned status %s for businessId %s", lei_resp.status, company.get("businessId"))
            except Exception as exc:
                logger.exception("Exception during LEI lookup for businessId %s", company.get("businessId"))
            # Compose enriched company data.
            enriched_company = {
                "companyName": company.get("companyName", "Unknown"),
                "businessId": company.get("businessId", "Unknown"),
                "companyType": company.get("companyType", "Unknown"),
                "registrationDate": company.get("registrationDate", "Unknown"),
                "status": company.get("status", "Unknown"),
                "lei": lei,
            }
            results.append(enriched_company)
        
        # Update the job record with enrichment results.
        try:
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
            logger.info("Enrichment process completed for job %s", search_id)
        except Exception as e:
            logger.exception("Failed to update job entity after processing: %s", e)

################################################################################
# POST endpoint to trigger company enrichment.
# It validates the incoming JSON request, adds a job entity using the external
# service with the workflow function, and returns the unique searchId.
################################################################################
@app.route("/api/company-enrichment", methods=["POST"])
@validate_request(CompanyRequest)  # Validation occurs on the request body
@validate_response(JobResponse, 202)
async def company_enrichment(data: CompanyRequest):
    requested_at = datetime.datetime.utcnow().isoformat()
    # job_data includes the companyName to be used by the workflow function.
    job_data = {
        "status": "pending",  # initial status; will be updated in workflow
        "requestedAt": requested_at,
        "results": None,
        "companyName": data.companyName,
    }
    try:
        # Add job entity with the process_job workflow.
        job_id = entity_service.add_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            entity=job_data,
            workflow=process_job
        )
    except Exception as e:
        logger.exception("Failed to add job entity: %s", e)
        return jsonify({"error": "Internal server error"}), 500
    return JobResponse(searchId=job_id, status="processing", requestedAt=requested_at), 202

################################################################################
# GET endpoint to retrieve enrichment results based on the searchId query parameter.
################################################################################
@validate_querystring(QueryJob)  # Validation occurs on query parameters
@app.route("/api/results", methods=["GET"])
async def results():
    search_id = request.args.get("searchId")
    if not search_id:
        return jsonify({"error": "Missing searchId query parameter"}), 400
    try:
        job = entity_service.get_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            technical_id=search_id
        )
    except Exception as e:
        logger.exception("Failed to retrieve job entity: %s", e)
        return jsonify({"error": "Internal server error"}), 500
    if not job:
        return jsonify({"error": "No job found with the provided searchId"}), 404
    return jsonify(job), 200

################################################################################
# Main entry point to run the Quart app.
################################################################################
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)