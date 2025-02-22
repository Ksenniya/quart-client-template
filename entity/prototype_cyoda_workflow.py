Below is the complete refactored application. In this version virtually all logic (including external API calls, enrichment, error handling, and even “fire‐and‐forget” tasks) has been moved out of the controller and into the asynchronous workflow function (process_companies). This approach minimizes the responsibilities of the endpoint functions and gives you a single place to modify the business logic. Comments explain each section while additional try/except blocks and validations help prevent potential issues (such as network errors, JSON parsing errors, or inconsistent entity data).

------------------------------------------------------------
#!/usr/bin/env python3
import asyncio
import datetime
import uuid
from dataclasses import dataclass
from typing import Optional

from quart import Quart, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response
import aiohttp

# Import required external service and related constants.
from common.config.config import ENTITY_VERSION
from app_init.app_init import cyoda_token, entity_service
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema for automatic validations

# Startup hook to initialize our external service (cyoda)
@app.before_serving
async def startup():
    try:
        await init_cyoda(cyoda_token)
    except Exception as e:
        # If initialization fails, log and abort early
        app.logger.error(f"Failed to initialize cyoda: {str(e)}")
        raise

# ---------------------------------------------------------------------------
# Workflow Function: process_companies
#
# This is the workflow function that is applied to the job entity BEFORE it is
# persisted by entity_service. It is entirely asynchronous, handles all external
# API calls, enrichment, error handling, and directly updates the local state of
# the entity (job) without using additional entity_service calls on the current
# entity model.
# ---------------------------------------------------------------------------
async def process_companies(entity: dict) -> dict:
    job_id = entity.get("id")
    external_api_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"

    # Prepare query parameters. Our initial job saved the minimal parameters we need.
    params = {}
    if entity.get("companyName"):
        params["name"] = entity["companyName"]

    # We create a dedicated session for our API calls.
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(external_api_url, params=params) as resp:
                if resp.status != 200:
                    # If the external call fails, mark the job as error.
                    entity["status"] = "error"
                    entity["result"] = {"error": "Failed to retrieve company data", "status_code": resp.status}
                    entity["workflowTimestamp"] = datetime.datetime.utcnow().isoformat()
                    return entity

                try:
                    external_data = await resp.json()
                except Exception as json_error:
                    # In case JSON decoding fails, catch the error.
                    entity["status"] = "error"
                    entity["result"] = {"error": f"Failed to decode response JSON: {str(json_error)}"}
                    entity["workflowTimestamp"] = datetime.datetime.utcnow().isoformat()
                    return entity

                companies = external_data.get("results", [])
    except Exception as network_error:
        # Catch exceptions due to network issues, etc.
        entity["status"] = "error"
        entity["result"] = {"error": f"Network error occurred: {str(network_error)}"}
        entity["workflowTimestamp"] = datetime.datetime.utcnow().isoformat()
        return entity

    # Filter out companies that are not active.
    active_companies = []
    for company in companies:
        # Defensive programming: make sure we compare lower-case strings.
        if isinstance(company.get("status"), str) and company.get("status").lower() == "active":
            active_companies.append(company)

    companies_result = []
    # Enrich each active company with additional data.
    # NOTE: The workflow function can launch asynchronous subtasks if needed (e.g. additional API calls),
    # but here we simply simulate an external LEI lookup.
    for company in active_companies:
        lei = "Not Available"
        try:
            # Simulate a LEI lookup; you can replace this with a real API call if needed.
            # For example:
            # async with session.get(lei_api_url, params={"businessId": company.get("businessId")}) as lei_resp:
            #     if lei_resp.status == 200:
            #         lei_data = await lei_resp.json()
            #         lei = lei_data.get("lei", "Not Available")
            #     else:
            #         lei = "Not Available"
            lei = "Mocked-LEI-12345"
        except Exception as lei_error:
            lei = "Not Available"
            app.logger.error(f"LEI lookup failed for company {company.get('businessId')}: {str(lei_error)}")

        company["lei"] = lei
        companies_result.append({
            "companyName": company.get("companyName", "Unknown"),
            "businessId": company.get("businessId", "Unknown"),
            "companyType": company.get("companyType", "Unknown"),
            "registrationDate": company.get("registrationDate", "Unknown"),
            "status": company.get("status", "Unknown"),
            "lei": company.get("lei")
        })

    # Modify the entity state directly. Since this entity is the one being persisted,
    # any changes here will be saved.
    entity["status"] = "completed"
    entity["result"] = companies_result
    entity["workflowTimestamp"] = datetime.datetime.utcnow().isoformat()

    # If needed, you can get or add supplementary entities here using a different entity_model.
    # Example:
    # supplementary_data = {"related": "info", "source": "external_api"}
    # entity_service.add_item(
    #     token=cyoda_token,
    #     entity_model="supplementary_data",
    #     entity_version=ENTITY_VERSION,
    #     entity=supplementary_data,
    #     workflow=None
    # )

    return entity

# ---------------------------------------------------------------------------
# Dataclass Definitions for Request/Response Validation
# These ensure that the POST payload includes the expected fields and that the
# returned JSON data satisfies the defined schema.
# ---------------------------------------------------------------------------
@dataclass
class LookupRequest:
    companyName: str        # The company name (full or partial) is required.
    location: Optional[str] = None
    businessId: Optional[str] = None
    registrationDateStart: Optional[str] = None  # Expected in yyyy-mm-dd format.
    registrationDateEnd: Optional[str] = None      # Expected in yyyy-mm-dd format.

@dataclass
class LookupResponse:
    searchId: str  # Identifier that clients can use for follow-up GET requests.

# ---------------------------------------------------------------------------
# POST Endpoint: /companies/lookup
#
# This endpoint is intentionally "thin". It creates a job entity containing the
# essential metadata as well as the minimal request payload needed for processing.
# Then it calls entity_service.add_item with the asynchronous workflow function,
# process_companies, which will apply all business logic before the entity is persisted.
# ---------------------------------------------------------------------------
@app.route('/companies/lookup', methods=['POST'])
@validate_request(LookupRequest)
@validate_response(LookupResponse, 202)
async def lookup_companies(data: LookupRequest):
    """
    Initiates a company lookup and enrichment process.

    The caller must supply at least a "companyName".
    Additional filtering criteria can be provided as well.

    The minimal job entity is created and the processing is handled asynchronously by
    the workflow function, process_companies.
    """
    # Generate a unique job id and record the request timestamp.
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()

    # Create the initial job entity. In addition to meta-data, we store the parameters
    # that the workflow function will need.
    job_data = {
        "id": job_id,
        "status": "processing",
        "requestedAt": requested_at,
        "result": None,
        # Save the incoming request data for processing.
        "companyName": data.companyName,
        "location": data.location,
        "businessId": data.businessId,
        "registrationDateStart": data.registrationDateStart,
        "registrationDateEnd": data.registrationDateEnd,
    }

    # Submit the job to the external service including the workflow function.
    # The workflow (process_companies) is applied asynchronously to the job entity before persistence.
    try:
        entity_service.add_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,  # Always use this constant
            entity=job_data,                # The job entity created above
            workflow=process_companies      # Asynchronous workflow function
        )
    except Exception as e:
        # In case storing the job fails, log the error and return an appropriate response.
        app.logger.error(f"Failed to add job entity: {str(e)}")
        abort(500, description="Internal Error: Unable to queue the job.")

    # Return the job id immediately to the client.
    return jsonify(LookupResponse(searchId=job_id)), 202

# ---------------------------------------------------------------------------
# GET Endpoint: /companies/<job_id>
#
# This endpoint retrieves the current state of the job entity using the external service.
# It returns the processing status if not yet completed, or the final enriched result.
# ---------------------------------------------------------------------------
@app.route('/companies/<job_id>', methods=['GET'])
async def get_companies(job_id):
    """
    Retrieve the status and result of a company lookup job.

    The client should supply the job identifier (searchId) returned by POST /companies/lookup.
    """
    try:
        job = entity_service.get_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
    except Exception as e:
        app.logger.error(f"Error retrieving job {job_id}: {str(e)}")
        abort(500, description="Internal Error: Unable to retrieve job.")

    if not job:
        abort(404, description="Job not found.")

    # Return different details depending on the current status.
    if job.get("status") == "processing":
        return jsonify({
            "status": "processing",
            "requestedAt": job.get("requestedAt")
        })
    elif job.get("status") == "error":
        return jsonify({
            "status": "error",
            "error": job.get("result")
        })
    else:
        return jsonify({
            "status": "completed",
            "result": job.get("result"),
            "completedAt": job.get("workflowTimestamp")
        })

# ---------------------------------------------------------------------------
# Run the Application.
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    # You may wish to disable threading when using async libraries; however,
    # we keep threaded=True as long as careful testing is performed.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
------------------------------------------------------------

Explanation & Considerations:
1. The POST endpoint (lookup_companies) creates a minimal job entity which is immediately submitted using entity_service.add_item.
   The workflow function, process_companies, takes over asynchronous processing – contacting external APIs,
   filtering and enriching the data – and updates the entity state directly.
2. process_companies handles different error scenarios (non-200 responses, JSON errors, network exceptions) and
   updates the entity state accordingly. It also adds a workflowTimestamp so that clients can see when processing completed.
3. No further add/update/delete calls are made on the same entity inside process_companies. Any supplementary data,
   if needed, can be stored under a different entity_model.
4. The GET endpoint fetches the entity and reports on its state ("processing", "error", or "completed").
5. Defensive error logging and exception propagation ensure that any issues (during service initialization,
   job saving, or retrieval) are captured and can be diagnosed.

This complete refactored application meets your requirements by “freeing” the controllers from excess logic while
centralizing asynchronous processing and enrichment inside the workflow function.