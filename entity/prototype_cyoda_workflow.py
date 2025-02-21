Below is the complete updated file. The changes are as follows:

1. We now pass a workflow function (process_companies) to entity_service.add_item. This workflow function is applied to the job entity before it is persisted. In our implementation process_companies inspects the job details and (as a side effect) schedules a background task to perform the actual processing (process_entity).

2. The explicit scheduling of process_entity in the POST endpoint has been removed because process_companies now handles that. Note that process_entity (and fetch_lei) remain unchanged.

Below is the complete updated code:

-------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
from datetime import datetime
from dataclasses import dataclass

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response

# Import the constant and the cyoda startup/init facilities.
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
# Adding QuartSchema.
QuartSchema(app)

# Add startup code.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Dataclass for the incoming POST payload.
@dataclass
class CompanyQuery:
    company_name: str
    registration_date_start: str = ""  # Expected format yyyy-mm-dd; empty string if not provided.
    registration_date_end: str = ""    # Expected format yyyy-mm-dd; empty string if not provided.
    page: int = 1

# Dataclass for the response of a job request.
@dataclass
class JobResponse:
    job_id: str
    status: str

# Async function to process company data: query the PRH API, filter, and enrich with LEI data.
async def process_entity(job_id: str, query_data: dict, requested_at: str):
    company_name = query_data.get("company_name")
    registration_date_start = query_data.get("registration_date_start")
    registration_date_end = query_data.get("registration_date_end")
    page = query_data.get("page", 1)
    
    # Build query parameters for the Finnish Companies Registry API.
    prh_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
    params = {"name": company_name, "page": page}
    if registration_date_start:
        params["registrationDateStart"] = registration_date_start
    if registration_date_end:
        params["registrationDateEnd"] = registration_date_end
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(prh_url, params=params) as resp:
                prh_data = await resp.json()
                # TODO: Adapt the parsing of prh_data based on the actual API response format.
    except Exception as e:
        # Update the external job record with failure.
        updated_job = {
            "job_id": job_id,
            "status": "failed",
            "requestedAt": requested_at,
            "error": f"Error fetching data from PRH: {str(e)}"
        }
        entity_service.update_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            entity=updated_job,
            meta={}
        )
        return

    # For demonstration purposes, assume the response contains a key "results" listing companies.
    companies = prh_data.get("results", [])
    # If no companies were returned, create a dummy record for demo purposes.
    if not companies:
        companies = [{
            "company_name": "Demo Company",
            "business_id": "1234567-8",
            "company_type": "OY",
            "registration_date": "2020-01-01",
            "status": "Active"
        }]
    
    # Filter out companies that are not active.
    active_companies = [c for c in companies if c.get("status", "").lower() == "active"]
    
    enriched_results = []
    # Enrich each active company with LEI data.
    for company in active_companies:
        lei = await fetch_lei(company)
        # Add the LEI information to the company record.
        company["lei"] = lei if lei else "Not Available"
        enriched_results.append(company)
    
    # Update the job using the external service.
    updated_job = {
        "job_id": job_id,
        "status": "done",
        "results": enriched_results,
        "requestedAt": requested_at,
        "completedAt": datetime.utcnow().isoformat()
    }
    entity_service.update_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        entity=updated_job,
        meta={}
    )

# Helper function that simulates fetching LEI details from an external service.
async def fetch_lei(company: dict) -> str:
    # TODO: Replace with an actual call to a LEI provider API when available.
    async with aiohttp.ClientSession() as session:
        # Simulate a delay that might occur when calling an external service.
        await asyncio.sleep(1)
        business_id = company.get("business_id", "")
        # Dummy logic: return a fake LEI if the business_id ends with an even digit.
        if business_id and business_id[-1] in "02468":
            return "LEI-" + business_id
        else:
            return None

# Workflow function for companies.
# This function takes the job entity as its only argument and is applied asynchronously
# before the entity is persisted. Here we use it to schedule the actual background processing.
async def process_companies(entity: dict) -> dict:
    # Extract details needed to process the job.
    job_id = entity.get("job_id")
    query_data = entity.get("query", {})
    requested_at = entity.get("requestedAt")
    # Schedule processing as a background task.
    asyncio.create_task(process_entity(job_id, query_data, requested_at))
    # Return the (possibly modified) entity. In this case, we do not change it.
    return entity

# POST endpoint to initiate the query processing.
# WORKAROUND: For POST requests, due to a quart-schema issue, the route decorator must come first,
# followed by @validate_request and then the @validate_response decorator.
@app.route("/companies/query", methods=["POST"])
@validate_request(CompanyQuery)
@validate_response(JobResponse, 200)
async def companies_query(data: CompanyQuery):
    # Convert dataclass to dict.
    query_data = data.__dict__
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()
    # Create initial job record.
    job = {
        "job_id": job_id,
        "status": "processing",
        "requestedAt": requested_at,
        "query": query_data
    }
    # Use the external service to add the job. The add_item call now also takes the workflow function.
    stored_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        entity=job,
        workflow=process_companies  # Workflow function applied asynchronously before persistence.
    )
    # Return the job id and initial status.
    return JobResponse(job_id=stored_id, status="processing")

# GET endpoint to retrieve the result of a previously submitted query.
# No validation decorator is needed for GET requests without a request body.
@app.route("/companies/result/<job_id>", methods=["GET"])
async def companies_result(job_id: str):
    # Retrieve job using the external entity_service.
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        return jsonify({"error": "Job not found"}), 404

    if job.get("status") == "processing":
        return jsonify({"job_id": job_id, "status": "processing"})
    elif job.get("status") == "failed":
        return jsonify({"job_id": job_id, "status": "failed", "error": job.get("error")}), 500
    else:
        return jsonify({
            "job_id": job_id,
            "status": "done",
            "results": job.get("results"),
            "metadata": {"completedAt": job.get("completedAt")}
        })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
-------------------------------------------------

In this version, the POST endpoint creates the initial job record and passes it to entity_service.add_item along with the workflow function. The workflow function (process_companies) immediately schedules the background processing and then returns the entity, letting the external service persist it.