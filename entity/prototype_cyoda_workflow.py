Below is one possible refactoring. In this version we “free” the endpoint from any asynchronous background logic by moving all enrichment‐steps into the workflow function (here named process_companies). That function is passed as a parameter to entity_service.add_item and is invoked asynchronously before the record is persisted. (Remember: within the workflow you may modify the passed entity’s state directly but you must not use entity_service.add/update/delete on the current entity_model.)

In our refactored approach the endpoint simply builds a minimal job record (now also storing the original request data under an “input” key so that the workflow function can use it), and then calls add_item with process_companies as the workflow. The workflow function itself (running asynchronously) first marks the job “processing”, then (using helper functions to call external APIs such as the Finnish Companies Registry and an LEI service) gathers enriched company details, and finally updates the same entity’s state with the results and “completed” status. This eliminates the need for a separate fire‐and‐forget background task.

Below is complete updated code:

------------------------------------------------
#!/usr/bin/env python3
import asyncio
from datetime import datetime
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response
import aiohttp

# Import external services and constants.
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Initialize request/response validation

# -------------------------------------------------------------------------
# Startup: Initialize any external systems before serving requests.
# -------------------------------------------------------------------------
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

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
# Helper Functions (External API calls)
# -------------------------------------------------------------------------
async def fetch_company_data(session: aiohttp.ClientSession, company_name: str):
    """
    Query the Finnish Companies Registry API using the provided company name.
    (Adjust the URL/parameters according to the actual API.)
    """
    params = {"name": company_name}
    async with session.get("https://avoindata.prh.fi/opendata-ytj-api/v3/companies", params=params) as resp:
        if resp.status == 200:
            data = await resp.json()
            return data.get("results", [])
        else:
            # TODO: Implement robust error handling.
            return []

async def lookup_lei(session: aiohttp.ClientSession, company: dict):
    """
    Lookup the Legal Entity Identifier (LEI) for the company.
    This is a placeholder: the logic here must be replaced with a real LEI lookup as needed.
    """
    await asyncio.sleep(0.1)  # Simulate latency.
    if len(company.get("companyName", "")) % 2 == 0:
        return "5493001KJTIIGC8Y1R12"
    else:
        return "Not Available"

# -------------------------------------------------------------------------
# Workflow Function for the 'companies' entity
#
# This function is invoked asynchronously by entity_service.add_item right before
# persisting the entity. It takes the entity data dictionary as its only argument.
# You may change this entity state as needed (e.g., add/modify attributes).
# IMPORTANT: You cannot call add/update/delete methods on the current entity model.
# However, you can get or add supplementary data for a different entity_model.
# -------------------------------------------------------------------------
async def process_companies(entity: dict) -> dict:
    """
    Pre-persistence workflow: Enriches a companies job record based on its input.
    
    The process includes:
      • Marking the job as "processing"
      • Fetching company data from an external source by companyName (provided in entity['input'])
      • Filtering active companies and looking up LEI values for each.
      • Updating the entity state with the enrichment results and marking the job "completed".
    """
    # Mark the job record as processing.
    entity["status"] = "processing"
    
    # Retrieve the original input data stored in the entity.
    input_data = entity.get("input", {})
    company_name = input_data.get("companyName")
    
    enriched_companies = []
    if company_name:
        async with aiohttp.ClientSession() as session:
            companies = await fetch_company_data(session, company_name)
            
            # Consider only active companies.
            active_companies = [comp for comp in companies if comp.get("status", "").lower() == "active"]
    
            for comp in active_companies:
                lei_val = await lookup_lei(session, comp)
                enriched_companies.append({
                    "companyName": comp.get("companyName", "Unknown"),
                    "businessId": comp.get("businessId", "Unknown"),
                    "companyType": comp.get("companyType", "Unknown"),
                    "registrationDate": comp.get("registrationDate", "Unknown"),
                    "status": "Active",
                    "LEI": lei_val,
                })
    
    # Update the entity with results and mark the job complete.
    entity["results"] = enriched_companies
    entity["status"] = "completed"
    entity["completedAt"] = datetime.utcnow().isoformat()
    
    # You can also add extra meta-data if needed.
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
    Initiates company data enrichment. Instead of launching an external asynchronous
    background task, we now pass a workflow function (process_companies) to entity_service.add_item.
    
    The endpoint builds an initial job record (which here also stores the original input data)
    and delegates the enrichment work entirely to process_companies, which is executed asynchronously
    before the entity is persisted.
    """
    requested_at = datetime.utcnow().isoformat()
    # Build the initial job record. Note the additional "input" key (containing the request data)
    # is provided so the workflow has access to the companyName and any other parameters.
    job_data = {
        "status": "queued",
        "requestedAt": requested_at,
        "results": None,
        "input": data.__dict__
    }
    
    # Persist the job record; process_companies is automatically invoked asynchronously to enrich the record.
    job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,  # Always use this constant
        entity=job_data,                # Initial job record state
        workflow=process_companies      # Workflow function for pre-persistence processing
    )
    
    return jsonify({
        "jobId": job_id,
        "message": "Enrichment processing started. Use the jobId to retrieve results."
    }), 202

@app.route("/companies/results/<job_id>", methods=["GET"])
async def get_results(job_id: str):
    """
    Retrieves the enriched result of a given job id.
    The job record is fetched from the persistent store.
    """
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        return jsonify({"error": "Job not found"}), 404

    if job.get("status") != "completed":
        return jsonify({
            "jobId": job_id,
            "status": job.get("status"),
            "message": "Results are not ready yet."
        }), 202

    return jsonify({
        "jobId": job_id,
        "results": job.get("results", [])
    }), 200

if __name__ == '__main__':
    # threaded=True allows asynchronous background tasks to work in this prototype.
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
------------------------------------------------

Key Points in this Refactoring:

1. All the enrichment logic (previously in a fire‐and‐forget task) has been moved inside process_companies.
2. The process_companies workflow function is asynchronous and directly modifies the incoming entity state.
3. The endpoint is now “lean” – it merely constructs the job record and delegates processing.
4. If additional supplementary data is needed (or processing on a different entity_model), that logic can be added inside process_companies. 

This approach leads to more robust code with thinner controllers and a clearer separation between request handling and business logic.