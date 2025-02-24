Below is an implementation for prototype.py. This prototype uses aiohttp for external HTTP calls and Quart for building the API. Note that external calls are mocked with TODO comments, and persistence is implemented with a simple in‐memory dictionary. Please review and adjust the TODO sections as the requirements become more complete.

--------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
import logging

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema  # One-liner as required

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Global in-memory storage for jobs; keys are search IDs.
jobs = {}

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def process_entity(search_id, request_data):
    """
    Processing task:
      1. Call the Finnish Companies Registry API with the provided companyName.
      2. Filter out inactive companies.
      3. For each active company, call an external LEI lookup API.
      4. Save enriched results in the jobs cache.
    """
    results = []
    company_name = request_data.get("companyName")
    # TODO: Add any additional filters from request_data if needed

    async with aiohttp.ClientSession() as session:
        # 1. Retrieve data from the Finnish Companies Registry API
        registry_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
        params = {"name": company_name}
        try:
            async with session.get(registry_url, params=params) as resp:
                if resp.status != 200:
                    logger.error("Finnish Registry API request failed with status %s", resp.status)
                    # TODO: Depending on requirements, update job status with error details.
                    jobs[search_id]["status"] = "error"
                    jobs[search_id]["error"] = f"Registry API returned status {resp.status}"
                    return
                registry_data = await resp.json()
        except Exception as e:
            logger.exception("Exception during Finnish Registry API request")
            jobs[search_id]["status"] = "error"
            jobs[search_id]["error"] = str(e)
            return

        # TODO: Adjust the data model according to actual API response.
        # For the prototype, assume registry_data is a dict containing a key 'results' that is a list of companies.
        companies = registry_data.get("results", [])
        logger.info("Retrieved %d companies from registry", len(companies))

        # 2. Filter out inactive companies and retain only active names from companies with multiple names
        active_companies = []
        for company in companies:
            # Assuming company has a 'status' key marking "Active" or "Inactive"
            if company.get("status", "").lower() == "active":
                active_companies.append(company)

        logger.info("Filtered to %d active companies", len(active_companies))

        # 3. For each active company, call an external LEI lookup service
        for company in active_companies:
            # TODO: Replace the dummy URL and logic with a real LEI lookup service.
            lei_service_url = "https://dummy-lei-lookup.com/api/lei"
            # Use businessId as a key for LEI lookup if available.
            params = {"businessId": company.get("businessId")}  # Adjust as necessary
            try:
                async with session.get(lei_service_url, params=params) as lei_resp:
                    if lei_resp.status == 200:
                        lei_data = await lei_resp.json()
                        lei = lei_data.get("lei", "Not Available")
                    else:
                        lei = "Not Available"
                        logger.warning("LEI service returned status %s", lei_resp.status)
            except Exception as e:
                logger.exception("Exception during LEI lookup for company %s", company.get("businessId"))
                lei = "Not Available"

            # Prepare the enriched record
            enriched_company = {
                "companyName": company.get("companyName", "Unknown"),
                "businessId": company.get("businessId", "Unknown"),
                "companyType": company.get("companyType", "Unknown"),
                "registrationDate": company.get("registrationDate", "Unknown"),
                "status": company.get("status", "Unknown"),
                "lei": lei,
            }
            results.append(enriched_company)

        # 4. Update job record with results and mark processing as complete.
        jobs[search_id]["status"] = "done"
        jobs[search_id]["completedAt"] = datetime.datetime.utcnow().isoformat()
        jobs[search_id]["results"] = results
        logger.info("Completed processing job %s", search_id)


@app.route("/api/company-enrichment", methods=["POST"])
async def company_enrichment():
    """
    POST endpoint to trigger company enrichment.
    Expects JSON like: {"companyName": "Example Company"}.
    Returns a searchId for later retrieval.
    """
    request_data = await request.get_json()
    if not request_data or "companyName" not in request_data:
        return jsonify({"error": "Missing companyName in request"}), 400

    # Create a unique job id
    search_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()

    # Save initial job information in the in-memory cache
    jobs[search_id] = {
        "status": "processing",
        "requestedAt": requested_at,
        "results": None,
    }

    # Fire and forget the processing task.
    asyncio.create_task(process_entity(search_id, request_data))
    return jsonify({"searchId": search_id, "status": "processing", "requestedAt": requested_at}), 202


@app.route("/api/results", methods=["GET"])
async def results():
    """
    GET endpoint to retrieve enrichment results using a searchId query parameter.
    Example: GET /api/results?searchId=<job_uuid>
    """
    search_id = request.args.get("searchId")
    if not search_id:
        return jsonify({"error": "Missing searchId query parameter"}), 400

    job = jobs.get(search_id)
    if job is None:
        return jsonify({"error": "No job found with the provided searchId"}), 404

    return jsonify(job), 200


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

--------------------------------------------------

Note the following:
• External API calls (Finnish Registry and LEI lookup) are implemented with aiohttp.ClientSession. Actual URL endpoints and data models might need updating.
• A simple in-memory dictionary (jobs) is used as a placeholder for persistence.
• Asynchronous processing is handled via asyncio.create_task to mimic fire-and-forget processing.
• TODO comments indicate where proper implementations or clarifications are needed.

This prototype should help verify the UX and identify any gaps before moving to a more robust implementation.