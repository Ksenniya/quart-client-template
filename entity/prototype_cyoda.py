Below is one possible refactored version of the code. In this version all local persistence via the in‑memory dictionary (search_results) is replaced by calls to the external entity_service. In the POST /api/companies/search endpoint the search results payload is sent to entity_service.add_item (using the entity_model "companies" and the constant ENTITY_VERSION imported from common.config.config) and the returned id is included in the response. In the GET /api/companies/result/<search_id> endpoint the result is retrieved via entity_service.get_item. (Any business logic such as fetching data from external APIs, filtering or enriching responses is left unchanged.) 

Note: If there were additional interactions with local in‑memory dictionaries for other entity types in your full codebase, you would refactor those similarly—by replacing direct dictionary access with the respective entity_service call using one of the supported methods.

Below is the updated prototype.py:

------------------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
from dataclasses import dataclass
from typing import List
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response  # also available: validate_querystring
import aiohttp

# Import the external entity_service and related constants
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # one‑line initialization as required

# Note: the in‑memory dict “search_results” has been removed. Instead, we use entity_service.

# External API endpoints (constants)
PRH_API_ENDPOINT = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
# Placeholder LEI API endpoint. TODO: Replace with actual LEI data provider details.
LEI_API_ENDPOINT = "https://api.mocklei.example.com/getLei"

# --- Startup Related Code ---
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

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
    equals "Active" (case‑insensitive).
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
    caches the results via entity_service.add_item, and returns a response including a searchId.
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

    # Step 4: Create a payload to be cached.
    ts = asyncio.get_event_loop().time()  # TODO: Replace with proper timestamp formatting if needed.
    cache_payload = {
        "results": enriched_results,
        "message": "Search executed successfully",
        "timestamp": ts
    }

    # Instead of storing in a local dictionary, use entity_service.add_item to cache the result.
    # The returned id (search id) is added to the response so that the client can query using this id.
    search_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=cache_payload  # the validated data object
    )

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
    # Retrieve the search results from the external entity service via search_id.
    result = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=search_id
    )
    if not result:
        return jsonify({"error": f"Result not found for searchId: {search_id}"}), 404

    # Return the result that was cached.
    return jsonify(result)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
------------------------------------------------------------

Notes:
• The POST endpoint now uses entity_service.add_item to persist the search result instead of relying on an in‑memory dictionary. The returned search_id is included in the JSON response.
• The GET endpoint retrieves the stored result via entity_service.get_item, returning an error message if no entity is found.
• All existing business logic (fetching, filtering, enriching data) remains intact.
• The required startup code to initialize cyoda is included via the @app.before_serving decorated function.
• Replace "companies" with the actual entity model name if needed.
• Only the allowed entity_service functions are used for interactions with the external cache/persistence.

This refactoring preserves the overall endpoint routes and business logic, while replacing the local cache with external service calls.