Below is an example of how you can refactor your code so that the heavy‐lifting logic (calling external APIs, enrichment, etc.) is moved into the workflow function. In this design the controller simply creates a minimal job (with a “processing” status) and passes it along with the workflow function (process_companies) to entity_service.add_item. Since the workflow function supports asynchronous calls, you can perform (and await) all the external API calls and enrichment logic there. When you change the entity’s local state (for example, setting status or result fields) the new state is ultimately persisted. (Remember, you must not use entity_service.add/update/delete on the same entity model when processing the “current” entity.) 

A few notes on the refactoring:
1. The POST endpoint is now “thin” – it only creates and submits a job for processing.
2. All processing logic has been moved into process_companies.
3. process_companies is defined as an asynchronous function. It calls external services and then modifies the entity state (job data) before it is finally persisted.  
4. You can also use process_companies to create supplementary entities using a different entity_model if needed.

Below is the complete refactored code:

------------------------------------------------------------
#!/usr/bin/env python3
import asyncio
import datetime
import uuid
from dataclasses import dataclass
from typing import Optional

from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response
import aiohttp

# Import the required external service and related constants.
from common.config.config import ENTITY_VERSION
from app_init.app_init import cyoda_token, entity_service
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Add cyoda startup initialization.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# This workflow function will be applied to the job entity BEFORE it is persisted.
# It performs all asynchronous processing logic – e.g. calling external APIs and enriching
# the job data.
async def process_companies(entity: dict) -> dict:
    job_id = entity["id"]
    external_api_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"

    # Build query parameters from the original request which we store in the entity.
    # (Assume that for raw input data we could have stored the request payload inside entity.)
    # In this example, for simplicity we re-use the companyName from the entity data.
    # (You may extend this to include additional filtering parameters.)
    params = {}
    if entity.get("companyName"):
        params["name"] = entity["companyName"]

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(external_api_url, params=params) as resp:
                if resp.status != 200:
                    # Mark the job as error if the external API fails.
                    entity["status"] = "error"
                    entity["result"] = {"error": "Failed to retrieve company data."}
                    return entity

                external_data = await resp.json()
                companies = external_data.get("results", [])
    except Exception as e:
        entity["status"] = "error"
        entity["result"] = {"error": f"Exception occurred: {str(e)}"}
        return entity

    # Filter out companies that are not active (adjust logic as needed).
    active_companies = [company for company in companies if company.get("status", "").lower() == "active"]

    companies_result = []
    # Enrich each active company with additional data (for example LEI lookup).
    for company in active_companies:
        lei = "Not Available"
        try:
            # Example external LEI lookup (you could also add a raw data entity with a different model).
            # Uncomment and modify if using a real lookup API.
            # lei_api_url = "https://example-lei-api.com/lookup"
            # async with session.get(lei_api_url, params={"businessId": company.get("businessId")}) as lei_resp:
            #     if lei_resp.status == 200:
            #         lei_data = await lei_resp.json()
            #         lei = lei_data.get("lei", "Not Available")
            #     else:
            #         lei = "Not Available"
            lei = "Mocked-LEI-12345"
        except Exception:
            lei = "Not Available"
        company["lei"] = lei

        companies_result.append({
            "companyName": company.get("companyName", "Unknown"),
            "businessId": company.get("businessId", "Unknown"),
            "companyType": company.get("companyType", "Unknown"),
            "registrationDate": company.get("registrationDate", "Unknown"),
            "status": company.get("status", "Unknown"),
            "lei": company.get("lei")
        })

    # Now update the entity state.
    entity["status"] = "completed"
    entity["result"] = companies_result

    # You can modify additional attributes of the entity here if needed.
    # For example, add a workflow timestamp:
    entity["workflowTimestamp"] = datetime.datetime.utcnow().isoformat()

    return entity

# Dataclass definitions for request/response validations.
@dataclass
class LookupRequest:
    companyName: str  # Required – full or partial company name.
    location: Optional[str] = None    # Optional – additional filtering.
    businessId: Optional[str] = None  # Optional
    registrationDateStart: Optional[str] = None  # Optional, format yyyy-mm-dd
    registrationDateEnd: Optional[str] = None    # Optional, format yyyy-mm-dd

@dataclass
class LookupResponse:
    searchId: str  # Identifier to poll for completed results.

# The POST endpoint is now very thin.
# It creates the job entity and passes it to the external entity_service along with the workflow function.
@app.route('/companies/lookup', methods=['POST'])
@validate_request(LookupRequest)
@validate_response(LookupResponse, 202)
async def lookup_companies(data: LookupRequest):
    """
    POST endpoint to trigger company lookup and enrichment.
    The JSON payload must include at least "companyName" (full or partial).
    """
    # Generate a job id and a timestamp.
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()

    # Create the initial job data.
    # In addition to the job meta-data we also store the minimal necessary payload (such as companyName)
    # for processing. The workflow function will enrich this data.
    job_data = {
        "id": job_id,
        "status": "processing",
        "requestedAt": requested_at,
        "result": None,
        # Save the original request details if needed by the workflow:
        "companyName": data.companyName,
        "location": data.location,
        "businessId": data.businessId,
        "registrationDateStart": data.registrationDateStart,
        "registrationDateEnd": data.registrationDateEnd,
    }

    # Instead of launching a separate fire-and-forget task,
    # we pass the workflow function which will be invoked asynchronously
    # to adjust the entity state. (Do not use entity_service.add_item for further updates on the job!)
    entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_data,               # the payload to save and enrich
        workflow=process_companies     # The workflow function performing asynchronous job processing.
    )

    # Return the job id immediately to the client.
    return jsonify(LookupResponse(searchId=job_id)), 202

# GET endpoint for retrieving results.
# It fetches the job data from the external service and returns its current state.
@app.route('/companies/<job_id>', methods=['GET'])
async def get_companies(job_id):
    """
    GET endpoint to retrieve results of a previous lookup using searchId.
    Returns the processing status if the result is not yet complete.
    """
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )

    if not job:
        abort(404, description="Job not found.")

    if job.get("status") == "processing":
        return jsonify({"status": "processing", "requestedAt": job.get("requestedAt")})
    elif job.get("status") == "error":
        return jsonify({"status": "error", "error": job.get("result")})
    else:
        return jsonify({"status": "completed", "result": job.get("result")})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
------------------------------------------------------------

Explanation:

• By shifting processing logic to process_companies (which is provided as the workflow function),
  the endpoint is freed from the responsibility of managing asynchronous calls and data enrichment.
• The workflow function receives the job entity as its only argument. Within process_companies,
  we call external APIs, perform enrichment, and update the entity’s internal state.
• No entity_service.add/update/delete call is made within the workflow function on the current entity.
  Instead, we directly modify the data (for example changing "status" or adding "result"),
  and the final state will then be persisted.
• This approach makes your controllers “thin” and your code more robust, since all the complex
  business logic is isolated inside a single workflow function that can be independently tested
  and updated while keeping the API endpoints simple.

Using this design, any asynchronous task – including fire-and-forget behavior – is now handled as part
of the workflow. This aligns well with your requirement to “free” the controllers from excess logic.