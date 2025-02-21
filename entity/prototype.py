Below is the prototype.py file that implements a working prototype using Quart, QuartSchema, aiohttp for external HTTP calls, and a simple in‑memory cache for persistence. Remember that many parts (such as the actual Finnish Companies Registry URL and the LEI service URL) are mocked/simulated. Wherever a more robust implementation is needed, you’ll see a TODO comment.

------------------------------------------------------------
#!/usr/bin/env python3
"""
Prototype for Finnish Companies Data Retrieval and Enrichment Application.
This prototype exposes a GET /companies endpoint, which:
  • Searches companies by name (and optionally other filters)
  • Filters out inactive companies
  • Enriches each active company with its Legal Entity Identifier (LEI)
  
External calls are currently mocked using aiohttp.ClientSession with placeholder URLs.
Persistence is simulated using a local in-memory cache.
"""

import asyncio
import aiohttp
import logging
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

# Create the Quart app instance
app = Quart(__name__)
QuartSchema(app)  # required line for QuartSchema usage

# Setup a very simple in-memory cache for persistence (mock)
local_lei_cache = {}  # { businessId: lei }

# Setup logging for debugging purposes
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def fetch_companies_from_registry(params: dict) -> list:
    """
    Fetch companies from the external Finnish Companies Registry.
    Uses aiohttp to execute an HTTP GET request.
    NOTE: This is a placeholder for the actual API call.
    
    TODO: Replace the URL with the actual Finnish Companies Registry endpoint.
    TODO: Handle pagination and proper parameter mapping.
    """
    # For now, we simulate an external API call with hardcoded sample data.
    # In a real implementation, you would use params to filter the search.
    simulated_response = [
        {
            "companyName": "Example Company",
            "businessId": "1234567-8",
            "companyType": "OY",
            "registrationDate": "2020-01-01",
            "status": "Active"
        },
        {
            "companyName": "Inactive Company",
            "businessId": "8765432-1",
            "companyType": "OY",
            "registrationDate": "2019-05-15",
            "status": "Inactive"
        }
    ]
    
    # Example of how you might use aiohttp for a real call:
    # async with aiohttp.ClientSession() as session:
    #     url = "https://api.actual-finregistry.example/companies"  # TODO: update to real URL
    #     async with session.get(url, params=params) as resp:
    #         if resp.status != 200:
    #             raise Exception("Error fetching companies from external registry")
    #         simulated_response = await resp.json()
    
    logger.debug("Simulated companies from registry: %s", simulated_response)
    return simulated_response


async def get_lei(business_id: str) -> str:
    """
    Fetch the Legal Entity Identifier (LEI) for a company.
    Uses aiohttp to execute an HTTP GET request.
    
    If the LEI has been previously fetched, returns the cached version.
    
    TODO: Replace the URL with the actual LEI enrichment service endpoint.
    """
    # Check if already cached
    if business_id in local_lei_cache:
        logger.debug("Returning cached LEI for business_id %s", business_id)
        return local_lei_cache[business_id]

    # For prototype purposes, we simulate a network call for LEI enrichment
    async with aiohttp.ClientSession() as session:
        # TODO: Replace with the actual LEI endpoint
        url = "https://api.example.lei/enrich"
        params = {"businessId": business_id}
        try:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.warning("Non-200 response from LEI service for business_id %s", business_id)
                    pass  # For the prototype, we continue even on error
                # In a real implementation, parse the response JSON:
                # data = await resp.json()
                # lei = data.get("lei")
                # For now, simulate a LEI value:
                lei = "LEI" + business_id.replace("-", "")
        except Exception as e:
            logger.error("Error fetching LEI for business_id %s: %s", business_id, e)
            # TODO: Handle exception appropriately
            lei = "UNKNOWN_LEI"
    
    # Cache the result
    local_lei_cache[business_id] = lei
    logger.debug("Caching LEI for business_id %s: %s", business_id, lei)
    return lei


async def enrich_companies_with_lei(companies: list) -> list:
    """
    For each active company in the provided list, fetch and attach the LEI.
    """
    tasks = []
    for company in companies:
        # Only enrich companies with status "Active"
        if company.get("status", "").lower() == "active":
            tasks.append(enrich_single_company(company))
    if tasks:
        await asyncio.gather(*tasks)
    return companies


async def enrich_single_company(company: dict):
    """
    Get the LEI for a single company and attach it to the company dict.
    """
    business_id = company.get("businessId")
    if business_id:
        lei = await get_lei(business_id)
        company["lei"] = lei
    else:
        company["lei"] = None  # or handle as desired
        logger.warning("No businessId provided for company: %s", company.get("companyName"))


@app.route("/companies", methods=["GET"])
async def get_companies():
    """
    GET /companies Endpoint.
    
    Expects a query parameter "name" along with optional filtering fields.
    Retrieves companies from Finnish Companies Registry, filters out inactive companies,
    enriches active companies with LEI and returns a JSON list of results.
    
    Responses:
      200: JSON list of companies.
      400: Bad Request for missing parameters.
      500: Internal Server Error for unexpected issues.
    """
    try:
        # Extract query parameters
        query_params = request.args.to_dict()
        if "name" not in query_params or not query_params["name"]:
            return jsonify({"error": "Missing required parameter: name"}), 400

        logger.debug("Received query_params: %s", query_params)
        
        # Fetch companies data from external registry (simulated)
        companies = await fetch_companies_from_registry(query_params)
        
        # Filter out inactive companies
        active_companies = [c for c in companies if c.get("status", "").lower() == "active"]
        logger.debug("Filtered active companies: %s", active_companies)
        
        # Enrich active companies with LEI information by fetching from an external service
        await enrich_companies_with_lei(active_companies)
        
        # Prepare final result. Note: For prototype purposes we only return active companies.
        return jsonify(active_companies), 200

    except Exception as e:
        logger.exception("Unexpected error in GET /companies")
        return jsonify({"error": "An unexpected error occurred"}), 500


# Entry point to run the Quart app
if __name__ == '__main__':
    # Start the Quart server using the given entry point specifications.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
------------------------------------------------------------

Notes:
• The external API calls (the Finnish Companies Registry and the LEI enrichment service) are simulated. Replace the placeholder URLs and response handling with appropriate logic once their details are available.
• Persistence is handled by a simple dictionary (local_lei_cache), which is only suitable for this prototype.
• No data input validations (beyond checking for a required “name” query parameter) have been added; the use of QuartSchema is included as requested, but no request validation decorators are applied.
• The code uses asyncio.gather to perform LEI fetches concurrently.
• Logging provides insight into the internal workflow for debugging and UX verification.

This prototype should support the UX review and help identify any additional gaps before proceeding with a more thorough implementation.