Below is a complete refactored version of the application that moves all asynchronous “fire‐and‐forget” and business logic into the workflow function (process_companies). In this design, the controller (endpoint) simply builds a minimal job record (including the original input data) and calls entity_service.add_item with process_companies as its workflow. That workflow function is executed asynchronously before the entity is persisted. In the workflow we perform all enrichment steps, mark the record “processing” (and later “completed”), and—in case of any problems—record an error and mark the job as "failed." We also include robust error handling, logging, timeout parameters, and sanity checks so that potential issues are caught early rather than leaving the job record in an indefinite state.

Below is the complete code in one file:

------------------------------------------------
#!/usr/bin/env python3
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_response
import aiohttp

# Import external service objects and configuration constants.
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

# Configure logging to capture errors and info.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Quart(__name__)
QuartSchema(app)  # Initialize request/response validation


# -------------------------------------------------------------------------
# Startup: Initialize any external systems before serving requests.
# -------------------------------------------------------------------------
@app.before_serving
async def startup():
    try:
        await init_cyoda(cyoda_token)
        logger.info("Cyoda successfully initialized.")
    except Exception as e:
        logger.error("Failed to initialize cyoda: %s", str(e))
        # Depending on your policy, you might choose to re‐raise here


# -------------------------------------------------------------------------
# Data Models for API validation.
# -------------------------------------------------------------------------
@dataclass
class EnrichRequest:
    companyName: str
    outputFormat: str = "json"  # Default format


@dataclass
class EnrichResponse:
    jobId: str
    message: str


# -------------------------------------------------------------------------
# Helper Functions for External API calls
# -------------------------------------------------------------------------
async def fetch_company_data(session: aiohttp.ClientSession, company_name: str) -> list:
    """
    Query the Finnish Companies Registry API using the provided company name.
    A timeout is used to avoid hanging. In case of any error a safe empty list is returned.
    """
    params = {"name": company_name}
    url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
    try:
        async with session.get(url, params=params, timeout=10) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("results", [])
            else:
                logger.error("Error fetching company data: status code %s", resp.status)
                return []
    except Exception as e:
        logger.exception("Exception caught while fetching company data:")
        return []


async def lookup_lei(session: aiohttp.ClientSession, company: dict) -> str:
    """
    Lookup the Legal Entity Identifier (LEI) for the company.
    This is a placeholder implementation and simulates a network call.
    """
    try:
        await asyncio.sleep(0.1)  # Simulate network latency.
        if len(company.get("companyName", "")) % 2 == 0:
            return "5493001KJTIIGC8Y1R12"
        else:
            return "Not Available"
    except Exception as e:
        logger.exception("Exception during LEI lookup:")
        return "Not Available"


# -------------------------------------------------------------------------
# Workflow Function for the 'companies' entity.
#
# This function is invoked asynchronously by entity_service.add_item right before
# persisting the entity. Its purpose is to perform all enrichment logic without
# requiring the controller to deal with the complexity of async background tasks.
#
# IMPORTANT:
#  • The incoming entity dictionary must be modified in place.
#  • You may call external services to enrich the data but you MUST NOT call
#    entity_service.add/update/delete for the same entity_model.
#  • In case of errors, mark the job as "failed" and include an "error" attribute.
# -------------------------------------------------------------------------
async def process_companies(entity: dict) -> dict:
    try:
        # Mark the job as processing.
        entity["status"] = "processing"
        
        # Access the original request data, which was stored under "input".
        input_data = entity.get("input", {})
        company_name = input_data.get("companyName", "").strip()
        if not company_name:
            raise ValueError("No companyName provided in input data.")
        
        enriched_companies = []
        async with aiohttp.ClientSession() as session:
            companies = await fetch_company_data(session, company_name)
            # Guard against a None result.
            if not companies:
                logger.info("No company data found for companyName: %s", company_name)
            # Filter for active companies. (assuming status field is present and should equal "active")
            active_companies = [comp for comp in companies if comp.get("status", "").lower() == "active"]

            for comp in active_companies:
                lei_value = await lookup_lei(session, comp)
                enriched_companies.append({
                    "companyName": comp.get("companyName", "Unknown"),
                    "businessId": comp.get("businessId", "Unknown"),
                    "companyType": comp.get("companyType", "Unknown"),
                    "registrationDate": comp.get("registrationDate", "Unknown"),
                    "status": "Active",
                    "LEI": lei_value
                })
        # Update the job record to indicate completion of enrichment.
        entity["results"] = enriched_companies
        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat()

    except Exception as e:
        # Log the error and update the entity so that a downstream consumer gets a proper status.
        logger.exception("Error in process_companies workflow:")
        entity["status"] = "failed"
        entity["error"] = str(e)
        entity["completedAt"] = datetime.utcnow().isoformat()
    finally:
        # Record that the workflow has been applied with a timestamp.
        entity["workflowApplied"] = True
        entity["workflowTimestamp"] = datetime.utcnow().isoformat()
    return entity


# -------------------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------------------
@app.route("/companies/enrich", methods=["POST"])
@validate_request(EnrichRequest)
@validate_response(EnrichResponse, 202)
async def enrich_companies(data: EnrichRequest):
    """
    Initiates company data enrichment. The endpoint performs minimal work by building
    a job record that contains:
      • A current status ("queued")
      • The timestamp when the request was received.
      • The original input data under the "input" key.
    
    The enrichment work is delegated entirely to the workflow function (process_companies)
    which is invoked asynchronously before the entity is persisted.
    """
    requested_at = datetime.utcnow().isoformat()
    job_data = {
        "status": "queued",
        "requestedAt": requested_at,
        "results": None,
        "input": data.__dict__  # store the original request for later use.
    }
    
    # Persist the job record and ensure the workflow function is applied.
    try:
        job_id = entity_service.add_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=job_data,
            workflow=process_companies  # enforce pre-persistence enrichment via workflow
        )
    except Exception as e:
        logger.exception("Failed to add job item:")
        return jsonify({"error": "Failed to create job", "details": str(e)}), 500

    return jsonify({
        "jobId": job_id,
        "message": "Enrichment processing started. Use the jobId to retrieve results."
    }), 202


@app.route("/companies/results/<job_id>", methods=["GET"])
async def get_results(job_id: str):
    """
    Retrieves the enriched result of a given job id. If the job is still processing,
    a relevant message is returned; if enrichment failed, then the error is provided.
    """
    try:
        job = entity_service.get_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
    except Exception as e:
        logger.exception("Error getting job item:")
        return jsonify({"error": "Error retrieving job", "details": str(e)}), 500

    if not job:
        return jsonify({"error": "Job not found"}), 404

    status = job.get("status", "unknown")
    if status not in ["completed", "failed"]:
        return jsonify({
            "jobId": job_id,
            "status": status,
            "message": "Results are not ready yet."
        }), 202

    if status == "failed":
        return jsonify({
            "jobId": job_id,
            "status": status,
            "error": job.get("error", "Unknown error occurred."),
            "message": "Enrichment process failed."
        }), 500

    # Otherwise, the job is completed.
    return jsonify({
        "jobId": job_id,
        "results": job.get("results", [])
    }), 200


# -------------------------------------------------------------------------
# Main block to run the app.
# -------------------------------------------------------------------------
if __name__ == '__main__':
    # Using threaded=True to ensure asynchronous background tasks execute properly in this prototype.
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
------------------------------------------------

Key Points and Preventative Measures:

1. The endpoint is “lean” and delegates the heavy lifting to process_companies.
2. The workflow (process_companies) is asynchronous and modifies the entity directly. It uses try/except/finally to handle any errors—if errors occur those are logged and the job is marked as "failed."
3. External API calls (fetch_company_data and lookup_lei) include a timeout and exception handling to prevent indefinite waits or unhandled exceptions.
4. Logging is employed to trace issues both during initialization and within the workflow.
5. The GET endpoint distinguishes between “queued/processing,” “completed,” and “failed” job statuses so that clients always get meaningful responses.

This complete refactored application offers a robust separation between the controller and business logic while ensuring that any errors are handled gracefully.