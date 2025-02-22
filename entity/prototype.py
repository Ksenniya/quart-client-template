Below is the updated prototype.py file with dataclasses and proper placement of validation decorators. Note that the GET endpoint uses no validation because it does not accept a request body or query parameters. Also, a comment is included to explain the decorator ordering workaround for Quart Schema.

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

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# In-memory job cache. In production, use a persistent storage.
entity_jobs = {}


# Dataclass definitions for request/response validations
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


# The POST endpoint uses App.route first, then validation decorators.
# (Workaround: For POST endpoints, the route decorator must be placed first, followed by @validate_request
# and then @validate_response, to satisfy the current quart-schema ordering requirements.)
@app.route('/companies/lookup', methods=['POST'])
@validate_request(LookupRequest)
@validate_response(LookupResponse, 202)
async def lookup_companies(data: LookupRequest):
    """
    POST endpoint to trigger company lookup and enrichment.
    The JSON payload must include at least "companyName" (full or partial).
    """
    # Create a job ID and store initial job info in the in-memory cache.
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at, "result": None}

    # Fire-and-forget the processing task.
    # We pass data.__dict__ to get a dictionary of the input values.
    asyncio.create_task(process_entity(job_id, data.__dict__))

    # Immediately return a searchId to the client.
    return jsonify(LookupResponse(searchId=job_id)), 202


async def process_entity(job_id: str, payload: dict):
    """
    Process the company lookup and enrichment.
      - Invokes the Finnish Companies Registry API to get company data.
      - Filters out inactive companies.
      - For each active company, invokes (a mock) LEI lookup.
      - Saves the enriched result in the global entity_jobs cache.
    """
    companies_result = []
    external_api_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"

    # Build query parameters from payload.
    params = {}
    if payload.get("companyName"):
        params["name"] = payload["companyName"]
    # TODO: Include optional parameters such as location, businessId, registrationDateStart, registrationDateEnd, etc.

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(external_api_url, params=params) as resp:
                if resp.status != 200:
                    # If the external call fails, mark the job as error.
                    entity_jobs[job_id]["status"] = "error"
                    entity_jobs[job_id]["result"] = {"error": "Failed to retrieve company data."}
                    return
                external_data = await resp.json()
                # TODO: Adapt this extraction according to the actual response structure.
                companies = external_data.get("results", [])
        except Exception as e:
            entity_jobs[job_id]["status"] = "error"
            entity_jobs[job_id]["result"] = {"error": f"Exception occurred: {str(e)}"}
            return

        # Filter out inactive companies.
        active_companies = []
        for company in companies:
            # TODO: Update the filtering logic based on the actual field names.
            # For our prototype we assume a field "status" exists and "active" indicates an active company.
            if company.get("status", "").lower() == "active":
                active_companies.append(company)

        # Enrich each active company with LEI data.
        for company in active_companies:
            # TODO: Replace mocked LEI lookup with a real API call if/when available.
            lei = "Not Available"
            try:
                # Example external LEI lookup:
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

            # Compose final company output. Adjust keys as needed based on data source.
            companies_result.append({
                "companyName": company.get("companyName", "Unknown"),
                "businessId": company.get("businessId", "Unknown"),
                "companyType": company.get("companyType", "Unknown"),
                "registrationDate": company.get("registrationDate", "Unknown"),
                "status": company.get("status", "Unknown"),
                "lei": company.get("lei")
            })

    # Save the result in our in-memory cache.
    entity_jobs[job_id]["status"] = "completed"
    entity_jobs[job_id]["result"] = companies_result


# GET endpoint for retrieving results.
# This endpoint does not have a request body; thus, no validation decorator is applied.
@app.route('/companies/<job_id>', methods=['GET'])
async def get_companies(job_id):
    """
    GET endpoint to retrieve results of a previous lookup using searchId.
    Returns the processing status if the result is not yet complete.
    """
    job = entity_jobs.get(job_id)
    if not job:
        abort(404, description="Job not found.")

    if job["status"] == "processing":
        return jsonify({"status": "processing", "requestedAt": job["requestedAt"]})
    elif job["status"] == "error":
        return jsonify({"status": "error", "error": job["result"]})
    else:
        return jsonify({"status": "completed", "result": job["result"]})


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

------------------------------------------------------------

Key notes:
• The POST endpoint (/companies/lookup) is decorated in the order required for POST requests:
 - First, app.route;
 - Then @validate_request (which converts JSON into a LookupRequest object);
 - Followed by @validate_response ensuring a LookupResponse instance is returned.
• The GET endpoint does not have request validation decorators.
• Mocks and TODO comments are included wherever external APIs or persistence logic is not fully defined.

This prototype should help evaluate the UX and identify any gaps in the requirements before proceeding further.