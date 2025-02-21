Below is the complete refactored application. In this version all “business‐logic” (including any fire‑and‑forget asynchronous tasks) has been moved into the workflow function (here named process_companies). The controllers (endpoints) only validate and forward the request data, while process_companies is responsible for contacting external services (the PRH API and the simulated LEI lookup), enriching the job entity, and handling errors robustly. We’ve also added extra validation and logging comments (feel free to swap in an actual logging framework) so that potential issues are caught early. Note that the workflow function directly changes the state of the current entity (it must not perform add/update/delete on the same entity_model!). 

────────────────────────────────────────────
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from dataclasses import dataclass

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring

# Import the external entity_service, cyoda_token and configuration constant.
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

# Optional: import logging for debugging purposes.
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Quart(__name__)
QuartSchema(app)  # initialize quart_schema

# ------------------------------------------------------------------------------
# Startup: Initialize external services at application start‐up.
# ------------------------------------------------------------------------------
@app.before_serving
async def startup():
    try:
        await init_cyoda(cyoda_token)
        logger.info("cyoda service initialized successfully.")
    except Exception as ex:
        logger.error("Failed to initialize cyoda: %s", str(ex))
        # Depending on needs, we might want to exit if the service doesn't initialize.
        raise

# ------------------------------------------------------------------------------
# Dataclasses for request validation.
# ------------------------------------------------------------------------------
@dataclass
class CompanySearchReq:
    name: str
    page: int = 1

@dataclass
class JobQuery:
    requestId: str

# ------------------------------------------------------------------------------
# Workflow function: process_companies
#
# This function is invoked by entity_service.add_item as the workflow and is applied
# to the entity just before it is persisted. It is an asynchronous function that can:
#   - Modify the entity in place (e.g., entity['attribute'] = new_value)
#   - Contact external endpoints and retrieve supplementary data.
#   - In case of exception, mark the entity with an error state.
#
# Note: You MUST NOT call entity_service.add/update/delete for the current (companies) entity.
# If needed, supplementary or raw data entities of a different entity_model can be added.
# ------------------------------------------------------------------------------
async def process_companies(entity: dict) -> dict:
    try:
        # Validate that the 'criteria' field exists and has necessary properties.
        criteria = entity.get("criteria")
        if not criteria or not criteria.get("name"):
            entity["status"] = "failed"
            entity["error"] = "Missing or invalid search criteria: company name is required."
            logger.error("Workflow failure: %s", entity["error"])
            return entity

        # Record the start time for processing (optional monitoring purposes)
        processing_started = datetime.datetime.utcnow().isoformat()
        entity["processingStarted"] = processing_started
        logger.info("Processing entity started at %s", processing_started)

        # Make external API calls in asynchronous context.
        import aiohttp
        async with aiohttp.ClientSession() as session:
            prh_api_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
            params = {"name": criteria.get("name"), "page": criteria.get("page", 1)}
            logger.info("Calling PRH API with params: %s", params)
            async with session.get(prh_api_url, params=params) as resp:
                if resp.status != 200:
                    logger.warning("PRH API returned non-200 status (%s), using empty results.", resp.status)
                    prh_data = {"results": []}  # Fallback to empty list
                else:
                    prh_data = await resp.json()

            # Filter for companies with "active" status.
            active_companies = []
            for company in prh_data.get("results", []):
                if company.get("status", "").lower() == "active":
                    active_companies.append(company)

            logger.info("Found %d active companies.", len(active_companies))

            # Enrich each active company with LEI data.
            enriched_results = []
            for company in active_companies:
                lei = await fetch_lei_for_company(company, session)
                enriched_company = {
                    "companyName": company.get("name", "N/A"),
                    "businessId": company.get("businessId", "N/A"),
                    "companyType": company.get("companyType", "N/A"),
                    "registrationDate": company.get("registrationDate", "N/A"),
                    "status": company.get("status", "N/A"),
                    "LEI": lei
                }
                enriched_results.append(enriched_company)

            # Update the entity in place with the enriched results.
            entity["results"] = enriched_results
            entity["completed"] = True
            entity["status"] = "completed"
            entity["processingEnded"] = datetime.datetime.utcnow().isoformat()
            logger.info("Workflow completed successfully for entity.")

    except Exception as e:
        # In case of any issues, catch the error and update the entity's state accordingly.
        entity["status"] = "failed"
        entity["error"] = str(e)
        logger.exception("Error during processing: %s", str(e))
    return entity

# ------------------------------------------------------------------------------
# Asynchronous utility function to fetch LEI data (mock implementation).
#
# In a real-world scenario, implement a call to an official LEI API.
# ------------------------------------------------------------------------------
async def fetch_lei_for_company(company: dict, session: aiohttp.ClientSession) -> str:
    try:
        # Simulate a network delay.
        await asyncio.sleep(0.1)
        # For demonstration purposes, return a placeholder.
        return "Not Available"
    except Exception as e:
        logger.error("Failed to fetch LEI for company: %s. Error: %s", company.get("name"), str(e))
        return "Error"

# ------------------------------------------------------------------------------
# POST endpoint: /api/v1/companies/search
#
# This endpoint receives search criteria, creates an initial job entity and delegates
# processing to the workflow function (process_companies) via entity_service.add_item.
# The workflow function will be invoked asynchronously before the entity is persisted.
# ------------------------------------------------------------------------------
@app.route('/api/v1/companies/search', methods=['POST'])
@validate_request(CompanySearchReq)
@validate_response(dict, 200)
async def search_companies(data: CompanySearchReq):
    # The minimal responsibility of the endpoint is to validate the input and prepare
    # the base job entity.
    if not data.name:
        logger.error("Validation failed: Company name is missing.")
        return jsonify({"error": "Company name is required"}), 400

    # Build initial job entity.
    requested_at = datetime.datetime.utcnow().isoformat()
    job_data = {
        "status": "processing",
        "requestedAt": requested_at,
        "criteria": data.__dict__
    }

    # Create a new unique identifier for the job. (This can also be generated inside entity_service.)
    created_id = str(uuid.uuid4())
    job_data["technical_id"] = created_id

    try:
        # Call the entity_service.add_item passing our workflow function.
        # The service will execute process_companies(entity) asynchronously before persisting.
        created_id = entity_service.add_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            entity=job_data,
            workflow=process_companies
        )
        logger.info("New job created with ID: %s", created_id)
    except Exception as e:
        logger.exception("Failed to create job entity: %s", str(e))
        return jsonify({"error": "Failed to initiate search", "details": str(e)}), 500

    # Return an immediate response. The job entity will be enriched asynchronously.
    return jsonify({
        "requestId": created_id,
        "status": "processing",
        "message": "Search initiated. Please poll the GET endpoint for results."
    })

# ------------------------------------------------------------------------------
# GET endpoint: /api/v1/companies/results
#
# This endpoint retrieves a job entity by its technical_id using entity_service.get_item.
# ------------------------------------------------------------------------------
@validate_querystring(JobQuery)
@app.route('/api/v1/companies/results', methods=['GET'])
async def get_results():
    requestId = request.args.get("requestId")
    if not requestId:
        logger.error("Missing requestId parameter.")
        return jsonify({"error": "requestId parameter is required"}), 400

    try:
        job = entity_service.get_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            technical_id=requestId
        )
    except Exception as e:
        logger.exception("Failed to retrieve job: %s", str(e))
        return jsonify({"error": "Could not retrieve job", "details": str(e)}), 500

    if not job:
        logger.warning("Job not found for ID: %s", requestId)
        return jsonify({"error": "Job not found"}), 404

    # Return the job details.
    return jsonify({
        "requestId": requestId,
        "results": job.get("results", []),
        "completed": job.get("completed", False),
        "status": job.get("status"),
        "requestedAt": job.get("requestedAt"),
        "processingStarted": job.get("processingStarted"),
        "processingEnded": job.get("processingEnded", None),
        "error": job.get("error", None)
    })

# ------------------------------------------------------------------------------
# Application entry point.
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
────────────────────────────────────────────

Explanation & Reasoning:

1. All heavy lifting is moved into process_companies (the workflow function). It is responsible for:
   • Validating the entity’s criteria.
   • Calling the PRH API asynchronously.
   • Filtering active companies.
   • Enriching companies with LEI data via fetch_lei_for_company.
   • Handling errors robustly by catching exceptions and updating the entity state.
2. The endpoint /api/v1/companies/search now only validates input and prepares the job entity. It hands over the processing to entity_service.add_item via the workflow parameter.
3. The GET endpoint /api/v1/companies/results simply retrieves the entity from entity_service.
4. We’ve added logging statements in key areas to help with debugging and to capture potential issues early.
5. All asynchronous operations are contained purely in functions that support await (avoiding blocking calls), ensuring robust asynchronous handling.
6. Crucially, the workflow does not call any add_item/update_item on the current entity_model—instead, it directly modifies and returns the entity. Any needed additional entities must be created with a different entity_model.

This design “frees” the controllers from excessive logic, focuses responsibilities clearly and prevents potential recursion issues by isolating persistence operations from in‐workflow changes.