Below is an example prototype for prototype.py. This code uses Quart, QuartSchema, and aiohttp.ClientSession to simulate the external API calls and in-memory persistence. Where requirements are unclear (such as the exact response format from external APIs), mocks and TODO comments are added to guide further development.

--------------------------------------------------

#!/usr/bin/env python3
import asyncio
import uuid
from quart import Quart, request, jsonify
from quart_schema import QuartSchema  # one-line initialization as required
import aiohttp

app = Quart(__name__)
QuartSchema(app)

# In-memory persistence for search results. For production, replace with real cache/persistence.
search_results = {}

# External API endpoints (constants)
PRH_API_ENDPOINT = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
# Placeholder LEI API endpoint. TODO: Replace with actual LEI data provider details.
LEI_API_ENDPOINT = "https://api.mocklei.example.com/getLei"

async def fetch_companies(company_name: str):
    """
    Fetch companies from the Finnish Companies Registry API using the provided company name.
    TODO: Adjust parsing based on actual API response structure.
    """
    params = {"name": company_name}
    async with aiohttp.ClientSession() as session:
        async with session.get(PRH_API_ENDPOINT, params=params) as resp:
            if resp.status != 200:
                # TODO: Enhance error handling based on actual response.
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

@app.route("/api/companies/search", methods=["POST"])
async def search_companies():
    """
    POST endpoint that accepts a JSON payload with a companyName.
    It performs an external search, filters active companies, enriches them with LEI data,
    caches the results, and returns a response including a searchId.
    """
    payload = await request.get_json()
    company_name = payload.get("companyName", "")
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
        enriched_results.append({
            "companyName": company.get("companyName") or company.get("name"),  # TODO: Adjust key names based on actual response.
            "businessId": company.get("businessId"),
            "companyType": company.get("companyType") or "Unknown",  # Placeholder if not provided.
            "registrationDate": company.get("registrationDate") or "Unknown",  # Placeholder
            "status": "Active",
            "lei": lei
        })

    # Step 4: Store the results in the in-memory cache with a generated searchId.
    search_id = str(uuid.uuid4())
    search_results[search_id] = {
        "results": enriched_results,
        "message": "Search executed successfully",
        "timestamp": asyncio.get_event_loop().time()  # TODO: Replace with proper timestamp formatting if needed.
    }

    # Step 5: Return response.
    return jsonify({
        "searchId": search_id,
        "results": enriched_results,
        "message": "Search executed successfully",
        "timestamp": asyncio.get_event_loop().time()
    })

@app.route("/api/companies/result/<string:search_id>", methods=["GET"])
async def get_search_result(search_id):
    """
    GET endpoint that retrieves a previously stored search result identified by searchId.
    """
    result = search_results.get(search_id)
    if not result:
        return jsonify({"error": f"Result not found for searchId: {search_id}"}), 404
    return jsonify(result)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

--------------------------------------------------

Notes:
• The external call to the PRH API uses aiohttp.ClientSession. Adjust parameter names or response parsing based on their actual API documentation.
• LEI enrichment is mocked based on a simple rule using the businessId. Replace this logic once the real data source is defined.
• Data persistence is done in an in-memory dictionary (“search_results”). Replace with a proper persistent store in a production implementation.
• The prototype uses dynamic payloads without strict request validation, as requested.

This prototype should help verify the user experience and expose any potential gaps in the requirements before a full implementation.