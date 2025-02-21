Below is the prototype.py file implementing the two endpoints with background processing, mocks for external APIs, local in‑memory caching, and placeholders for details to be refined later:

------------------------------------------------------------
#!/usr/bin/env python3
"""
Prototype for the Finnish Companies Data Retrieval and Enrichment Application.

This prototype implements:
  • POST /companies/search – to initiate the search and enrichment process.
  • GET /companies/results/{searchId} – to retrieve the processed results.

Notes:
  • All external HTTP calls (Finnish Companies Registry API and LEI lookup) are simulated
    using aiohttp and mocked responses.
  • Persistence is simulated using a local in‑memory cache (search_cache).
  • Quart API is used with QuartSchema for schema support.
  • Background processing is performed using asyncio.create_task.
  • TODO comments are added in places where requirements are unclear or where
    a real implementation needs to be provided.
"""

import asyncio
import uuid
import logging

from quart import Quart, request, jsonify
from quart_schema import QuartSchema  # Only installed and added for potential future schema validation
import aiohttp

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# In-memory cache to simulate persistence for search results.
# Dictionary format: {search_id: {"status": "processing"/"completed", "results": [...]}}
search_cache = {}

# Simulated external API endpoints (TODO: update with real endpoints)
FINNISH_REGISTRY_API_URL = "https://api.example.com/finnish-companies"  # TODO: Replace with actual Finnish Companies Registry API endpoint.
LEI_API_URL = "https://api.example.com/lei"  # TODO: Replace with actual LEI data source endpoint.


async def get_companies_from_registry(session: aiohttp.ClientSession, company_name: str, filters: dict) -> list:
    """
    Simulate a call to the Finnish Companies Registry API.

    In a real implementation, this would use session.get/post with the correct URL, parameters, 
    and error-handling logic.
    """
    # TODO: Implement actual API call with query parameters (filters) and error handling.
    logger.info("Simulating Finnish Registry API call for company: %s, with filters: %s", company_name, filters)
    # Simulated response containing two companies (one active, one inactive)
    await asyncio.sleep(0.5)  # simulate network delay
    simulated_response = [
        {
            "companyName": company_name,
            "businessId": "1234567-8",
            "type": "OY",
            "registrationDate": "2010-05-20",
            "status": "Active"
        },
        {
            "companyName": company_name,
            "businessId": "8765432-1",
            "type": "OY",
            "registrationDate": "2012-07-15",
            "status": "Inactive"
        }
    ]
    return simulated_response


async def get_lei_for_company(session: aiohttp.ClientSession, business_id: str) -> str:
    """
    Simulate fetching the LEI (Legal Entity Identifier) for a company.

    In a real implementation, this function would perform an HTTP request to the LEI data service.
    """
    # TODO: Replace simulated behavior with a real API call to fetch LEI data.
    logger.info("Simulating LEI lookup for businessId: %s", business_id)
    await asyncio.sleep(0.3)  # simulate network delay
    # For demonstration, we assume that active companies always return a valid LEI.
    return "5493001KJTIIGC8Y1R12"


async def process_company_search(search_id: str, request_data: dict) -> None:
    """
    Background processing for company search and enrichment.

    This function simulates:
        1. Querying the Finnish Companies Registry API.
        2. Filtering out inactive companies.
        3. Enriching each active company with its LEI.
    """
    try:
        company_name = request_data.get("companyName")
        filters = request_data.get("filters", {})  # e.g. registrationDateStart, registrationDateEnd

        async with aiohttp.ClientSession() as session:
            # 1. Retrieve companies from registry.
            companies = await get_companies_from_registry(session, company_name, filters)

            # 2. Filter out inactive companies.
            active_companies = [company for company in companies if company.get("status") == "Active"]

            # Handle case where no active companies found.
            if not active_companies:
                logger.info("No active companies found for searchId: %s", search_id)
                # Even if no active companies are found, mark status as completed with empty results.
                search_cache[search_id] = {"status": "completed", "results": []}
                return

            # 3. Enrich each active company with its LEI.
            # Use asyncio.gather to concurrently fetch LEI data.
            tasks = []
            for company in active_companies:
                business_id = company.get("businessId")
                tasks.append(get_lei_for_company(session, business_id))
            lei_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Consolidate enriched company data.
            enriched_companies = []
            for company, lei in zip(active_companies, lei_results):
                if isinstance(lei, Exception):
                    # If fetching LEI fails, set LEI as "Not Available".
                    logger.error("LEI lookup failed for businessId: %s", company.get("businessId"))
                    company["LEI"] = "Not Available"
                else:
                    company["LEI"] = lei if lei else "Not Available"
                enriched_companies.append(company)

            # Update cache with completed status and the processed results.
            search_cache[search_id] = {
                "searchId": search_id,
                "results": enriched_companies,
                "status": "completed"
            }
            logger.info("Processing completed for searchId: %s", search_id)
    except Exception as e:
        logger.exception("Error while processing searchId %s: %s", search_id, str(e))
        # On error, mark the search as completed with an error message (could be enhanced).
        search_cache[search_id] = {
            "searchId": search_id,
            "results": [],
            "status": "error",
            "error": str(e)
        }


@app.route('/companies/search', methods=['POST'])
async def companies_search():
    """
    POST /companies/search

    Initiates the process of data retrieval and enrichment.
    Returns a searchId and a processing status.
    """
    try:
        req_data = await request.get_json()
        if not req_data or "companyName" not in req_data:
            return jsonify({"error": "Invalid input, missing 'companyName'."}), 400

        # Create a unique search ID.
        search_id = str(uuid.uuid4())
        # Initialize cache entry with a processing state.
        search_cache[search_id] = {"status": "processing", "results": []}

        # Kick off background processing without blocking the request.
        asyncio.create_task(process_company_search(search_id, req_data))

        # Return initial response.
        response = {
            "searchId": search_id,
            "status": "processing"
        }
        return jsonify(response), 202

    except Exception as e:
        logger.exception("Error in /companies/search endpoint: %s", str(e))
        return jsonify({"error": "Internal server error."}), 500


@app.route('/companies/results/<search_id>', methods=['GET'])
async def companies_results(search_id):
    """
    GET /companies/results/{searchId}

    Retrieves the data processing results using the provided searchId.
    """
    try:
        # Retrieve results from the local in-memory cache.
        result = search_cache.get(search_id)
        if result is None:
            return jsonify({"error": "Search ID not found."}), 404

        # If processing is still ongoing, return the current state.
        if result.get("status") == "processing":
            return jsonify({
                "searchId": search_id,
                "results": [],
                "status": "processing"
            })

        # Otherwise, return the completed results. Structure as specified.
        return jsonify({
            "searchId": search_id,
            "results": result.get("results", []),
            "status": result.get("status")
        })

    except Exception as e:
        logger.exception("Error in /companies/results endpoint: %s", str(e))
        return jsonify({"error": "Internal server error."}), 500


if __name__ == '__main__':
    # Starting the application with the specified parameters.
    # Note: use_reloader is disabled to avoid duplicate background tasks during prototype testing.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

------------------------------------------------------------

Notes:
  • All external requests are made with aiohttp.ClientSession.
  • The prototype uses in‑memory storage (search_cache) to simulate persistence.
  • For production, replace the simulated API calls with real implementations and add robust error handling as needed.
  • The background processing is performed asynchronously using asyncio.create_task.
  • QuartSchema is initialized but dynamic input means we do not use @validate_request.
  
This prototype should serve to verify the UX and help identify any further gaps in the requirements.