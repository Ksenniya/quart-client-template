Below is the prototype.py file with the requested endpoints. This implementation uses Quart and aiohttp.ClientSession for async HTTP calls and mocks the external APIs and persistence (using local in‑memory caches). Wherever details are missing or are placeholders, you’ll see a TODO comment.

-------------------------
#!/usr/bin/env python3
"""
Prototype for Finnish Companies Data Retrieval and Enrichment Application.
Endpoints:
  • GET /companies – search for companies and return only active ones enriched with LEI.
  • GET /companies/<businessId>/lei – return the LEI for a specific company.
"""

import asyncio
from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # required single line configuration

# In-memory cache mocks for persistence
lei_cache = {}  # Cache for LEI responses (keyed by businessId)
companies_cache = {}  # TODO: Implement caching for companies search if needed later.

# Global aiohttp session object
aiohttp_session = None

# Set up the aiohttp session on startup and close it on shutdown.
@app.before_serving
async def create_aiohttp_session():
    global aiohttp_session
    aiohttp_session = aiohttp.ClientSession()

@app.after_serving
async def close_aiohttp_session():
    await aiohttp_session.close()

async def fetch_companies_from_registry(name: str, location: str, businessId: str, page: int):
    """
    Simulate an async call to the Finnish Companies Registry API.
    TODO: Replace this with a real API call using aiohttp_session.
    """
    # Simulate network latency
    await asyncio.sleep(0.1)
    # Dummy dataset for simulation purposes.
    dummy_data = [
        {
            "companyName": "Example Company",
            "businessId": "1234567-8",
            "companyType": "OY",
            "registrationDate": "2020-01-01",
            "status": "Active"
        },
        {
            "companyName": "Inactive Company",
            "businessId": "9876543-2",
            "companyType": "OY",
            "registrationDate": "2015-05-05",
            "status": "Inactive"
        }
    ]
    # Filter by businessId, if specified.
    if businessId:
        dummy_data = [comp for comp in dummy_data if comp['businessId'] == businessId]
    # Filter by name (simple substring case-insensitive match).
    dummy_data = [comp for comp in dummy_data if name.lower() in comp['companyName'].lower()]
    # TODO: Implement location filtering properly when external API supports it.
    # TODO: Implement a proper pagination mechanism based on page and page size.
    return dummy_data

async def fetch_lei_from_external_api(businessId: str):
    """
    Simulate an async call to a LEI external API.
    Uses a local in-memory cache to store responses.
    TODO: Replace URL and request details with the actual LEI API.
    """
    # Check if we already cached the LEI for this businessId.
    if businessId in lei_cache:
        return lei_cache[businessId]

    # Simulate an external API call (here we just wait briefly and create dummy value).
    await asyncio.sleep(0.05)
    # Dummy LEI generation (for demonstration purposes).
    dummy_lei = f"LEI-{businessId.replace('-', '')}"
    lei_cache[businessId] = dummy_lei
    return dummy_lei

@app.route('/companies', methods=['GET'])
async def search_companies():
    """
    GET /companies endpoint.
    Accepts query parameters:
      - name (string, required)
      - location (string, optional)
      - businessId (string, optional)
      - page (integer, default=1)
    Returns a JSON payload with the active companies enriched with LEI.
    """
    name = request.args.get('name')
    if not name:
        return jsonify({"error": "Parameter 'name' is required."}), 400
    location = request.args.get('location')
    businessId = request.args.get('businessId')
    page = request.args.get('page', 1, type=int)

    # Fetch companies from the Finnish Companies Registry (simulated).
    companies = await fetch_companies_from_registry(name, location, businessId, page)

    # Filter to include only active companies.
    active_companies = [comp for comp in companies if comp.get('status') == 'Active']

    # Enrich each active company with its LEI.
    # Gather tasks for asynchronous LEI retrieval.
    lei_tasks = [fetch_lei_from_external_api(comp['businessId']) for comp in active_companies]
    leis = await asyncio.gather(*lei_tasks)
    for comp, lei in zip(active_companies, leis):
        comp['lei'] = lei

    # For prototype, we are not doing detailed pagination.
    response = {
        "results": active_companies,
        "total": len(active_companies),
        "page": page
    }
    return jsonify(response), 200

@app.route('/companies/<businessId>/lei', methods=['GET'])
async def get_company_lei(businessId: str):
    """
    GET /companies/<businessId>/lei endpoint.
    Returns the LEI for the provided businessId.
    """
    lei = await fetch_lei_from_external_api(businessId)
    response = {
        "businessId": businessId,
        "lei": lei
    }
    return jsonify(response), 200

if __name__ == '__main__':
    # Entry point for running the Quart app.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

-------------------------

Notes:
• We use aiohttp.ClientSession (created in before_serving) for future external HTTP requests.
• Persistence is simulated with global dictionaries (lei_cache and companies_cache) instead of a database.
• Wherever real integration details are unavailable (e.g., external API endpoints or pagination), a TODO comment is added.
• This is a working prototype intended for UX verification and requirement gap identification.