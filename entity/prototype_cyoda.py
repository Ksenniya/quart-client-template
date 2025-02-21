Below is one acceptable “after” version. In this example the in‑memory cache (the “entity_jobs” dict) is removed. Instead, when a job is created the code “adds” an item via entity_service.add_item (passing a job record with status, requestedAt and no companies yet) and then “updates” that record later on via entity_service.update_item inside process_entity. Finally, the GET endpoint for a job calls entity_service.get_item instead of checking a local dictionary.

This example preserves the original business logic (calling external APIs, enriching companies with LEI data, etc.) while replacing the local cache with the allowed calls. (If some function seems insufficient, you might simply “skip” that update as instructed.) 

Below is the full refactored file:

------------------------------------------------------------
#!/usr/bin/env python3
""" 
Below is a working prototype implementation refactored so that interactions with the local in‑memory cache (entity_jobs)
are replaced by calls to an external service via entity_service.

Notes:
 • For a POST/PUT, the route decorator comes first, then validate_request, then validate_response.
 • For GET endpoints with query parameters, validate_querystring must be first.
 • All persistence is now done via the following calls:
      entity_service.add_item(…)
      entity_service.get_item(…)
      entity_service.update_item(…)
      etc.
 • The startup function initializes the external cyoda repository.
"""

import asyncio
import datetime
import logging
import uuid
import aiohttp

from dataclasses import dataclass
from typing import Optional

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring

# Import the external entity service and constants.
from common.config.config import ENTITY_VERSION
from app_init.app_init import cyoda_token, entity_service
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

# Constants for external API endpoints
PRH_API_URL = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
# TODO: Replace with an actual LEI API endpoint or use multiple sources if available.
LEI_API_URL = "https://example.com/lei"  # Placeholder for LEI data source

# Data Models for API validation.
@dataclass
class CompanySearchPayload:
    companyName: str
    registrationDateStart: Optional[str] = None
    registrationDateEnd: Optional[str] = None
    companyForm: Optional[str] = None

@dataclass
class JobResponse:
    resultId: str
    status: str
    message: str

# Startup code to initialize the external cyoda repository.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

async def fetch_lei_for_company(session: aiohttp.ClientSession, company: dict) -> str:
    # Placeholder implementation for LEI enrichment.
    # TODO: Implement real logic to call official LEI registries or reliable sources.
    await asyncio.sleep(0.1)  # simulate network latency
    # For demo purposes, return a mock LEI. In a real scenario, determine if lookup is successful.
    return "LEI1234567890" if company.get("businessId") else "Not Available"

async def process_entity(job_id: str, data: CompanySearchPayload):
    logging.info("Starting processing for job %s", job_id)
    try:
        async with aiohttp.ClientSession() as session:
            # Build the query parameters from the input data.
            params = {"name": data.companyName}
            if data.registrationDateStart:
                params["registrationDateStart"] = data.registrationDateStart
            if data.registrationDateEnd:
                params["registrationDateEnd"] = data.registrationDateEnd
            if data.companyForm:
                params["companyForm"] = data.companyForm

            # Call the external Finnish Companies Registry API.
            async with session.get(PRH_API_URL, params=params) as resp:
                if resp.status != 200:
                    # If response not OK, update the job with error details.
                    job = entity_service.get_item(
                        token=cyoda_token,
                        entity_model="companies",
                        entity_version=ENTITY_VERSION,
                        technical_id=job_id
                    )
                    job["status"] = "failed"
                    job["error"] = f"Failed retrieving data from PRH API, status code {resp.status}"
                    entity_service.update_item(
                        token=cyoda_token,
                        entity_model="companies",
                        entity_version=ENTITY_VERSION,
                        entity=job,
                        meta={}
                    )
                    return
                prh_data = await resp.json()

            # TODO: Adjust filtering as per actual API response layout.
            companies = prh_data.get("results", [])
            # Filter out inactive companies.
            active_companies = [comp for comp in companies if comp.get("status", "").lower() == "active"]

            # Enrich each active company with LEI information.
            for company in active_companies:
                lei = await fetch_lei_for_company(session, company)
                company["LEI"] = lei

            # Retrieve and update the job record via the external service.
            processed_job = entity_service.get_item(
                token=cyoda_token,
                entity_model="companies",
                entity_version=ENTITY_VERSION,
                technical_id=job_id
            )
            processed_job["companies"] = []
            for company in active_companies:
                processed_job["companies"].append({
                    "companyName": company.get("name"),
                    "businessId": company.get("businessId"),
                    "companyType": company.get("companyForm"),  # TODO: Verify mapping for company type.
                    "registrationDate": company.get("registrationDate"),
                    "status": company.get("status"),
                    "LEI": company.get("LEI")
                })
            processed_job["status"] = "completed"
            processed_job["completedAt"] = datetime.datetime.utcnow().isoformat()

            entity_service.update_item(
                token=cyoda_token,
                entity_model="companies",
                entity_version=ENTITY_VERSION,
                entity=processed_job,
                meta={}
            )

    except Exception as e:
        logging.exception("Error processing job %s", job_id)
        job = entity_service.get_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
        job["status"] = "failed"
        job["error"] = str(e)
        entity_service.update_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            entity=job,
            meta={}
        )

# POST Endpoint: Search Companies
@app.route("/companies/search", methods=["POST"])
@validate_request(CompanySearchPayload)  # For POST, validate_request comes after route decorator.
@validate_response(JobResponse, 202)
async def companies_search(data: CompanySearchPayload):
    # Create a new job record.
    requested_at = datetime.datetime.utcnow().isoformat()
    job = {
        "status": "processing",
        "requestedAt": requested_at,
        "companies": None
    }
    # Store job record using entity_service.
    job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        entity=job
    )

    # Fire and forget the asynchronous processing task passing the job_id.
    asyncio.create_task(process_entity(job_id, data))

    return JobResponse(
        resultId=job_id,
        status="processing",
        message="Your request is being processed."
    ), 202

# GET Endpoint: Retrieve Results
@app.route("/companies/results/<job_id>", methods=["GET"])
async def companies_results(job_id: str):
    # Retrieve the job record from the external service.
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
            "resultId": job_id,
            "status": job.get("status"),
            "message": "Processing not finished, please try again later."
        }), 202
    return jsonify({
        "resultId": job_id,
        "companies": job.get("companies")
    })

if __name__ == '__main__':
    # NOTE: In a production scenario, additional configuration may be needed.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
------------------------------------------------------------

Key changes made:
1. The in‑memory cache (“entity_jobs”) is removed.
2. When a POST request comes in at /companies/search, a job record is created via entity_service.add_item and the returned id is included in the response.
3. The background processing function (process_entity) now accepts the external job id, retrieves the corresponding record via entity_service.get_item, and once processing (including the LEI enrichment) completes, updates the record via entity_service.update_item.
4. The GET endpoint (/companies/results/<job_id>) now retrieves the job record using entity_service.get_item.
5. The required startup code with init_cyoda is added in a before_serving hook.
6. The business logic (data ingestion, external REST calls, enrichment, etc.) is preserved.

This should meet the requirements of refactoring the code to use external persistence while preserving the endpoints and business logic.