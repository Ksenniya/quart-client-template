Below is one complete example of how you could refactor the sample code. In the revised version all interactions with what was formerly an in‑memory cache (the entity_jobs dictionary) are now replaced with calls to the external entity_service functions. Note that the code uses only the allowed service functions; if more detailed operations were required but not available, we leave that logic “as is” (or simply update the record via update_item). Also, we add the startup code as specified and import ENTITY_VERSION from common.config.config. (In this example we assume that the “entity_model” for these endpoints is "companies" since the endpoints relate to company search/enrichment; adjust if necessary.) 

────────────────────────────────────────────
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from dataclasses import dataclass

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring  # Import decorators

# Import the external entity_service and startup token
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # One-line schema initialization

# -----------------------------
# Startup: Initialize the external cyoda service at application start‐up.
# -----------------------------
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# -----------------------------
# Dataclasses for request validation
# -----------------------------
@dataclass
class CompanySearchReq:
    name: str
    page: int = 1

@dataclass
class JobQuery:
    requestId: str

# -----------------------------
# Async function to process the external API calls and enrichment.
# -----------------------------
async def process_entity(job_id, criteria: CompanySearchReq):
    try:
        # Create an aiohttp ClientSession for external API calls.
        import aiohttp
        async with aiohttp.ClientSession() as session:
            prh_api_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
            params = {"name": criteria.name, "page": criteria.page}
            async with session.get(prh_api_url, params=params) as resp:
                if resp.status != 200:
                    # TODO: Handle non‑200 responses properly in production.
                    prh_data = {"results": []}  # Placeholder data when error occurs.
                else:
                    prh_data = await resp.json()

            # Filter companies for "active" status.
            active_companies = []
            for company in prh_data.get("results", []):
                if company.get("status", "").lower() == "active":
                    active_companies.append(company)

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
                    "LEI": lei,
                }
                enriched_results.append(enriched_company)

        # Build the update payload.
        update_data = {
            "results": enriched_results,
            "completed": True,
            "status": "completed"
        }
        # Replace the local cache update with an external service update.
        entity_service.update_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            entity=update_data,
            meta={"technical_id": job_id}  # Pass the job ID as metadata so the service knows which record to update.
        )
    except Exception as e:
        # In case of processing error, update the job status to failed.
        error_update = {
            "status": "failed",
            "error": str(e)
        }
        entity_service.update_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            entity=error_update,
            meta={"technical_id": job_id}
        )

# -----------------------------
# Async function to fetch LEI data (mock implementation).
# -----------------------------
async def fetch_lei_for_company(company, session):
    # TODO: Replace this mock with a call to an official LEI API or a reliable financial data source.
    await asyncio.sleep(0.1)  # Simulate network call delay.
    return "Not Available"  # Placeholder value if LEI is not found.

# -----------------------------
# POST endpoint to initiate company search and enrichment.
# Endpoint decorators: route, then validate_request, then validate_response.
# -----------------------------
@app.route('/api/v1/companies/search', methods=['POST'])
@validate_request(CompanySearchReq)
@validate_response(dict, 200)
async def search_companies(data: CompanySearchReq):
    # Validate input.
    if not data.name:
        return jsonify({"error": "Company name is required"}), 400

    # Generate a unique request/job ID.
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()

    # Build the initial job payload which includes the search criteria.
    job_data = {
        "status": "processing",
        "requestedAt": requested_at,
        "criteria": data.__dict__
    }

    # Instead of writing to local memory, add the job via entity_service.
    created_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        entity=job_data
    )

    # Fire‐and‐forget the external processing task.
    asyncio.create_task(process_entity(created_id, data))

    # Return response including the created job’s ID.
    return jsonify({
        "requestId": created_id,
        "status": "processing",
        "message": "Search initiated. Please poll the GET endpoint for results."
    })

# -----------------------------
# GET endpoint to retrieve the search results.
# For GET endpoints, the validate_querystring decorator must be applied before the route.
# -----------------------------
@validate_querystring(JobQuery)
@app.route('/api/v1/companies/results', methods=['GET'])
async def get_results():
    requestId = request.args.get("requestId")
    if not requestId:
        return jsonify({"error": "requestId parameter is required"}), 400

    # Retrieve the job using the external service.
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=requestId
    )
    if not job:
        return jsonify({"error": "Job not found"}), 404

    # Return the job details.
    return jsonify({
        "requestId": requestId,
        "results": job.get("results", []),
        "completed": job.get("completed", False),
        "status": job.get("status")
    })

# -----------------------------
# Application entry point
# -----------------------------
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
────────────────────────────────────────────

Explanation of key changes:
1. The global in‑memory dictionary (entity_jobs) is removed. Instead, when a job is initiated in search_companies the job details are sent to the external entity_service via add_item. The returned identifier (created_id) is used as the job identifier.
2. In process_entity the job record is updated with enrichment results using update_item. In case of processing errors, the job record is updated to “failed”.
3. The get_results endpoint now looks up the job record using entity_service.get_item.
4. The startup function is added (with the required imports) so that init_cyoda is called before the app starts serving requests.
5. The essential business logic—including the call to external APIs for enrichment and the LEI lookup call—is preserved.

This refactored code should now be fully integrated with the external entity_service while keeping the overall endpoint contracts and business logic intact.