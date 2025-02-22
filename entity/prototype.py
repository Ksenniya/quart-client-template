Below is a complete prototype.py that implements your requirements using Quart and aiohttp. Note that many external calls and persistence aspects are mocked with TODO comments so that we can later refine with real implementations.

------------------------------------------------------------
#!/usr/bin/env python3
import asyncio
import datetime
import uuid

from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# In-memory job cache. In production, use a persistent storage
entity_jobs = {}


async def process_entity(job_id: str, payload: dict):
    """
    Process the company lookup and enrichment.  
    This function:
      - Invokes the Finnish Companies Registry API to get company data.
      - Filters for active companies.
      - For each active company invokes (a mock) LEI lookup.
      - Saves the enriched result in the global entity_jobs cache.
    """
    companies_result = []
    external_api_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
    # Build query parameters from payload. For now, we're only using "companyName"
    # as per our requirements, but additional filtering parameters can be added.
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
                # Assume the external API returns a JSON with a field "results" (this is a placeholder).
                external_data = await resp.json()
                # TODO: Adapt this extraction according to the real response structure.
                companies = external_data.get("results", [])
        except Exception as e:
            entity_jobs[job_id]["status"] = "error"
            entity_jobs[job_id]["result"] = {"error": f"Exception occurred: {str(e)}"}
            return

        # Filter out inactive companies.
        active_companies = []
        for company in companies:
            # TODO: Update the filtering logic based on the actual field names provided by the API.
            # For our prototype, we assume a field "status" exists and active companies have "active" (case-insensitive).
            if company.get("status", "").lower() == "active":
                active_companies.append(company)

        # Enrich each active company with LEI information.
        for company in active_companies:
            # TODO: Replace with real LEI API call. Using a mocked value for now.
            lei = "Not Available"
            try:
                # Here you could make an external HTTP request to a LEI service if available.
                # For example:
                # lei_api_url = "https://example-lei-api.com/lookup"
                # async with session.get(lei_api_url, params={"businessId": company.get("businessId")}) as lei_resp:
                #     if lei_resp.status == 200:
                #         lei_data = await lei_resp.json()
                #         lei = lei_data.get("lei", "Not Available")
                #     else:
                #         lei = "Not Available"
                #
                # For now, we simply assign a mocked LEI value.
                lei = "Mocked-LEI-12345"
            except Exception as e:
                lei = "Not Available"
            company["lei"] = lei

            # Compose final company output. Adjust key mapping based on available data.
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


@app.route('/companies/lookup', methods=['POST'])
async def lookup_companies():
    """
    POST endpoint to trigger company lookup and enrichment.
    The request payload must include at least "companyName" (full or partial).
    """
    try:
        payload = await request.get_json()
    except Exception:
        abort(400, description="Invalid JSON payload.")

    if not payload or not payload.get("companyName"):
        abort(400, description="Missing required field: companyName")

    # Create a job ID and store initial job info in the in-memory cache.
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at, "result": None}

    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, payload))
    
    # Immediately return a searchId to the user.
    return jsonify({"searchId": job_id}), 202


@app.route('/companies/<job_id>', methods=['GET'])
async def get_companies(job_id):
    """
    GET endpoint to retrieve results of a previous lookup by searchId.
    Returns processing status if not complete.
    """
    job = entity_jobs.get(job_id)
    if not job:
        abort(404, description="Job not found.")

    # If processing, inform the client.
    if job["status"] == "processing":
        return jsonify({"status": "processing", "requestedAt": job["requestedAt"]})
    elif job["status"] == "error":
        return jsonify({"status": "error", "error": job["result"]})
    else:
        return jsonify({"status": "completed", "result": job["result"]})


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

------------------------------------------------------------

Comments on key areas:
• External API calls (Finnish Companies Registry and LEI services) are implemented via aiohttp.ClientSession. The actual response structure is assumed (TODO comments mark where adjustments may be necessary).
• In-memory caching is used via the global dictionary entity_jobs. In production, replace this with a proper persistence layer.
• The processing is fire-and-forget using asyncio.create_task, so the POST endpoint returns a searchId immediately.  
• The GET endpoint provides a way to poll the job status.

This prototype will help verify the overall user experience and highlight any gaps before a full implementation.