Below is the updated prototype.py that adds request/response validation using the quart‐schema decorators. In this example we define two simple dataclasses—one for the incoming search request and one for the search response (which includes an inner CompanyResult type). Note that the GET endpoint does not use validation for query parameters per the instructions.

-------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
from dataclasses import dataclass
from typing import List
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response  # also available: validate_querystring
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # one-line initialization as required

# In-memory persistence for search results. For production, replace with a real persistence/cache.
search_results = {}

# External API endpoints (constants)
PRH_API_ENDPOINT = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
# Placeholder LEI API endpoint. TODO: Replace with actual LEI data provider details.
LEI_API_ENDPOINT = "https://api.mocklei.example.com/getLei"

# --- Data Models for Validation ---

@dataclass
class CompanySearch:
    companyName: str

@dataclass
class CompanyResult:
    companyName: str
    businessId: str
    companyType: str
    registrationDate: str
    status: str
    lei: str

@dataclass
class SearchResponse:
    searchId: str
    results: List[CompanyResult]
    message: str
    timestamp: float

# --- Helper Functions ---

async def fetch_companies(company_name: str):
    """
    Fetch companies from the Finnish Companies Registry API using the provided company name.
    TODO: Adjust parsing based on actual API response structure.
    """
    params = {"name": company_name}
    async with aiohttp.ClientSession() as session:
        async with session.get(PRH_API_ENDPOINT, params=params) as resp:
            if resp.status != 200:
                # TODO: Enhance error handling based on the real API response.
                return []
            data = await resp.json()
            # Assume the external API returns a JSON object with a "results" key; adjust if necessary.
            companies = data.get("results", [])
            return companies

async def fetch_lei_info(company):
    """
    Enrich a company with LEI data.
    This is a mocked implementation. A real call would use aiohttp to contact an external LEI provider.
    TODO: Replace the mock logic with an actual HTTP request when API details become available.
    """
    business_id = company.get("businessId", "")
    # For the prototype, if the last digit of the businessId (ignoring hyphens) is even, we simulate a valid LEI.
    try:
        last_digit = int(business_id.replace("-", "")[-1])
    except Exception:
        last_digit = 1  # Default fallback if unable to parse
    if last_digit % 2 == 0:
        return f"MOCK_LEI_{business_id}"
    else:
        return "Not Available"

def filter_active_companies(companies):
    """
    Filter out companies that are not active.
    For this prototype, we assume a company is active if its 'status' field (or similar)
    equals "Active" (case-insensitive).
    TODO: Modify criteria if the real API uses a different field or value.
    """
    filtered = []
    for comp in companies:
        status = comp.get("status", "").lower()
        if status == "active":
            filtered.append(comp)
    return filtered

# --- Endpoints ---

@validate_request(CompanySearch)
@validate_response(SearchResponse, 200)
@app.route("/api/companies/search", methods=["POST"])
async def search_companies(data: CompanySearch):
    """
    POST endpoint that accepts a JSON payload with a companyName.
    It performs an external search, filters active companies, enriches them with LEI data,
    caches the results, and returns a response including a searchId.
    """
    company_name = data.companyName
    if not company_name:
        return jsonify({"error": "companyName is required"}), 400

    # Step 1: Fetch companies from the external PRH API.
    companies = await fetch_companies(company_name)
    if not companies:
        return jsonify({"error": "No companies found or error fetching companies"}), 404

    # Step 2: Filter out inactive companies.
    active_companies = filter_active_companies(companies)

    # Step 3: Enrich each active company with LEI information.
    enriched_results = []
    for company in active_companies:
        lei = await fetch_lei_info(company)
        enriched_results.append(CompanyResult(
            companyName=company.get("companyName") or company.get("name"),  # TODO: Adjust key names based on the actual response.
            businessId=company.get("businessId", ""),
            companyType=company.get("companyType") or "Unknown",  # Placeholder if not provided.
            registrationDate=company.get("registrationDate") or "Unknown",  # Placeholder
            status="Active",
            lei=lei
        ))

    # Step 4: Store the results in the in-memory cache with a generated searchId.
    search_id = str(uuid.uuid4())
    ts = asyncio.get_event_loop().time()  # TODO: Replace with proper timestamp formatting if needed.
    cache_payload = {
        "results": enriched_results,
        "message": "Search executed successfully",
        "timestamp": ts
    }
    search_results[search_id] = cache_payload

    # Step 5: Return response.
    return SearchResponse(
        searchId=search_id,
        results=enriched_results,
        message="Search executed successfully",
        timestamp=ts
    )

@app.route("/api/companies/result/<string:search_id>", methods=["GET"])
async def get_search_result(search_id):
    """
    GET endpoint that retrieves a previously stored search result identified by searchId.
    No input validation is required as there is no request body.
    """
    result = search_results.get(search_id)
    if not result:
        return jsonify({"error": f"Result not found for searchId: {search_id}"}), 404
    # Since the result was stored as a dict with enriched company results, return it directly.
    return jsonify(result)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

-------------------------------

Notes:
• The POST endpoint now uses @validate_request(CompanySearch) to automatically validate the incoming JSON payload.
• The response for the POST endpoint is validated using @validate_response(SearchResponse, 200) and relies on the newly defined dataclasses.
• The GET endpoint continues to use standard route parameters, as GET requests do not have a body for validation.
• Mocks and TODO comments are in place for external API details and persistence logic.

This prototype should support verifying the user experience (UX) and expose any gaps in the requirements before a more robust solution is implemented.