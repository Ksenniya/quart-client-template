Below is an updated version of prototype.py that adds request/response validations using quart-schema. Note that for POST endpoints the route is declared first and then the @validate_request and @validate_response decorators are added (this is a workaround for a known issue in quart-schema). For GET endpoints with query parameters, the validation decorator is placed before the route. In our current design the only GET endpoint (for results retrieval) does not require query validation.

In this prototype we define a simple CompanySearchRequest model (using only primitives) that carries the companyName (and optionally filters later). We also define a SearchResponse model for our POST response.

Below is the complete code:

--------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # Integrate QuartSchema

# Dataclass for request validation for the POST endpoint.
@dataclass
class CompanySearchRequest:
    companyName: str
    # TODO: Add additional filter fields if needed (must be primitives)

# Dataclass for response validation for the POST endpoint.
@dataclass
class SearchResponse:
    searchId: str
    status: str
    message: str

# Global in-memory cache for jobs and results
entity_jobs = {}

PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3"
# Placeholder URL for LEI data source
LEI_API_URL = "https://mock-lei-service.example.com/getLei"  # TODO: Replace with an official endpoint

async def fetch_companies_from_prh(company_name, filters):
    """
    Query PRH API for companies.
    """
    params = {"name": company_name}
    # TODO: Map additional filters to the query parameters if needed.
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{PRH_API_BASE}/companies", params=params) as response:
            if response.status == 200:
                data = await response.json()
                # TODO: Adjust based on actual API response structure.
                return data.get("results", [])
            else:
                # TODO: Handle/log errors appropriately.
                return []

async def fetch_lei_for_company(company):
    """
    Mock function to retrieve the LEI for a company.
    In a real implementation, this should call an official LEI registry.
    """
    # TODO: Replace this mock with actual logic to query the LEI service.
    await asyncio.sleep(0.2)  # Simulate network delay
    # For demonstration, companies with an even-length name get a valid LEI.
    if len(company.get("companyName", "")) % 2 == 0:
        return "VALID_LEI_MOCK"
    else:
        return "Not Available"

def is_company_active(company):
    """
    Determine whether a company is active.
    Assumes that the company data has a "status" key with value "Active" if active.
    TODO: Adjust logic based on actual data.
    """
    return company.get("status", "").lower() == "active"

async def process_entity(job_id, payload):
    """
    Background task to process company search and enrichment.
    """
    try:
        company_name = payload.get("companyName")
        filters = payload.get("filters", {})  # Currently unused; TODO: enhance filter mapping if needed

        # 1. Retrieve companies from PRH API
        companies = await fetch_companies_from_prh(company_name, filters)

        # 2. Filter out inactive companies
        active_companies = [company for company in companies if is_company_active(company)]

        # 3. Enrich each active company with LEI information
        enriched_companies = []
        for company in active_companies:
            lei = await fetch_lei_for_company(company)
            enriched_company = {
                "companyName": company.get("companyName", "Unknown"),   # TODO: Adjust key names per PRH response
                "businessId": company.get("businessId", "Unknown"),         # TODO: Adjust accordingly
                "companyType": company.get("companyType", "Unknown"),       # TODO: Adjust accordingly
                "registrationDate": company.get("registrationDate", "Unknown"),  # TODO: Adjust accordingly
                "status": "Active",
                "LEI": lei
            }
            enriched_companies.append(enriched_company)

        # 4. Update the in-memory cache record for the job.
        entity_jobs[job_id]["results"] = enriched_companies
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["completedAt"] = datetime.datetime.utcnow().isoformat()

    except Exception as e:
        entity_jobs[job_id]["status"] = "error"
        entity_jobs[job_id]["error"] = str(e)
        # TODO: Add proper logging here.

# POST endpoint: route first, then validation decorators (workaround for quart-schema issue)
@app.route("/companies/search", methods=["POST"])
@validate_request(CompanySearchRequest)  # Must be second in POST
@validate_response(SearchResponse, 200)
async def search_companies(data: CompanySearchRequest):
    """
    Triggers the company search and enrichment process.
    Expects a JSON body with at least a companyName.
    """
    payload = data.__dict__

    search_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()

    # Save job information in the in-memory cache.
    entity_jobs[search_id] = {
        "status": "processing",
        "requestedAt": requested_at,
        "results": None
    }

    # Fire-and-forget background task.
    asyncio.create_task(process_entity(search_id, payload))

    return SearchResponse(
        searchId=search_id,
        status="processing",
        message="Your search is being processed."
    )

# GET endpoint for results retrieval.
# No validation is needed because there are no query parameters for GET.
@app.route("/companies/results/<job_id>", methods=["GET"])
async def get_search_results(job_id):
    """
    Retrieves search results for a given search job identifier.
    """
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Invalid searchId"}), 404

    if job["status"] == "processing":
        return jsonify({
            "searchId": job_id,
            "status": "processing",
            "message": "Your search is still being processed, please try again later."
        })

    if job["status"] == "error":
        return jsonify({
            "searchId": job_id,
            "status": "error",
            "message": "There was an error processing your search.",
            "error": job.get("error")
        })

    return jsonify({
        "searchId": job_id,
        "results": job.get("results", []),
        "metadata": {
            "requestedAt": job.get("requestedAt"),
            "completedAt": job.get("completedAt"),
            "resultCount": len(job.get("results", []))
        }
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
--------------------------------------------------

Comments:
1. For POST endpoints the route decorator comes first followed by the validation decorators. This is a known workaround with quart-schema.
2. GET endpoints with query string parameters would have @validate_querystring placed before the route decorator; however, our GET endpoint does not require this since it relies solely on the path parameter.
3. Mocks and TODO comments are added wherever external services or persistence logic are uncertain.

This prototype should allow you to verify the UX and pinpoint any remaining gaps before a more complete implementation.