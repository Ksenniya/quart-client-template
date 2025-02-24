import asyncio
import uuid
import datetime
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response  # Workaround: For POST, decorators placed in order route then validate_request then validate_response
import aiohttp

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for persistence (mock)
entity_jobs = {}

# URL for external Finnish Companies Registry API (using v3 endpoint as provided)
PRH_API_URL = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"

# Placeholder URL for LEI lookup (TODO: replace with official LEI registry API)
LEI_API_URL = "https://lei.example.com/api/get"

# Data classes for request/response validation
@dataclass
class CompanySearchRequest:
    companyName: str
    filters: dict = None  # TODO: refine structure of filters if needed

@dataclass
class SearchResponse:
    requestId: str
    status: str
    message: str

async def fetch_companies(company_name, filters):
    """
    Fetch companies from the Finnish Companies Registry API.
    """
    params = {"name": company_name}
    # Add additional filters if provided
    if filters:
        params.update(filters)
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(PRH_API_URL, params=params) as response:
                # TODO: Adjust parsing according to the actual API response structure.
                if response.status == 200:
                    data = await response.json()
                    return data.get("results", [])  # Assuming a 'results' key with list of companies.
                else:
                    return []
        except Exception as e:
            # TODO: Add proper error logging.
            print(f"Error fetching companies: {e}")
            return []

async def fetch_lei(business_id):
    """
    Fetch the Legal Entity Identifier (LEI) for a given business ID.
    """
    params = {"businessId": business_id}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(LEI_API_URL, params=params) as response:
                # TODO: Adjust parsing according to the actual API response structure.
                if response.status == 200:
                    data = await response.json()
                    return data.get('lei', "Not Available")
                else:
                    return "Not Available"
        except Exception as e:
            # TODO: Add proper error logging.
            print(f"Error fetching LEI for {business_id}: {e}")
            return "Not Available"

async def process_entity(job, input_data):
    """
    Process the search request: fetch, filter, enrich and store the results.
    """
    company_name = input_data.companyName
    filters = input_data.filters if input_data.filters is not None else {}

    # Fetch companies from external API.
    companies = await fetch_companies(company_name, filters)

    # Filter out inactive companies.
    # TODO: Adjust the filtering logic if the status key or criteria differ.
    active_companies = [comp for comp in companies if comp.get("status", "").lower() == "active"]

    enriched_results = []
    # For each active company, fetch the LEI.
    for company in active_companies:
        business_id = company.get("businessId")
        lei = await fetch_lei(business_id)
        # Build enriched data structure.
        enriched_company = {
            "companyName": company.get("companyName"),
            "businessId": business_id,
            "companyType": company.get("companyType"),
            "registrationDate": company.get("registrationDate"),
            "status": "Active",
            "lei": lei
        }
        enriched_results.append(enriched_company)

    # Update job status and results.
    job["status"] = "completed"
    job["results"] = enriched_results
    job["completedAt"] = datetime.datetime.utcnow().isoformat()

@app.route("/companies/search", methods=["POST"])
@validate_request(CompanySearchRequest)  # For POST requests, decorators are placed after route decorator as a workaround for quart-schema issue.
@validate_response(SearchResponse, 201)
async def search_companies(data: CompanySearchRequest):
    """
    POST endpoint to trigger the company data retrieval, filtering, and enrichment process.
    """
    # Create a unique request/job ID.
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()
    # Mock persistence: store the job in in-memory cache.
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}

    # Fire and forget the processing task.
    asyncio.create_task(process_entity(entity_jobs[job_id], data))

    return jsonify({
        "requestId": job_id,
        "status": "processing",
        "message": "Your request is being processed. Retrieve results using GET /companies/result/{requestId}"
    }), 201

@app.route("/companies/result/<string:request_id>", methods=["GET"])
async def get_company_results(request_id):
    """
    GET endpoint to retrieve the enriched company data by request ID.
    """
    job = entity_jobs.get(request_id)
    if not job:
        return jsonify({"error": "Request ID not found"}), 404

    if job.get("status") != "completed":
        return jsonify({
            "requestId": request_id,
            "status": job.get("status"),
            "message": "Results are not yet ready. Please try again later."
        }), 202

    return jsonify({
        "requestId": request_id,
        "results": job.get("results", [])
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)