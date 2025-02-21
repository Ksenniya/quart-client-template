Below is the updated prototype.py with added Quart Schema validation. In this version, we define a dataclass CompanyQueryParams (using only primitives) to validate the query parameters for the GET /companies endpoint. We use the decorator @validate_querystring from quart_schema (note the order: the validation decorator comes first, then the route decorator). For any POST/PUT endpoints (if added later), you would use @validate_request. Please review the TODO comments for additional enhancements later.

------------------------------------------------------------
#!/usr/bin/env python3
"""
Prototype for Finnish Companies Data Retrieval and Enrichment Application.

This prototype exposes a GET /companies endpoint which:
  • Searches companies by name (and optional filters)
  • Filters out inactive companies
  • Enriches each active company with its Legal Entity Identifier (LEI)

External API calls are currently mocked using aiohttp.ClientSession with placeholder URLs.
Persistence is simulated using a local in-memory cache.
"""

import asyncio
import aiohttp
import logging
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_querystring  # For GET requests, use validate_querystring
from dataclasses import dataclass
from typing import Optional

# Create the Quart app instance and initialize QuartSchema
app = Quart(__name__)
QuartSchema(app)

# Define a dataclass for query parameters validation for GET /companies
@dataclass
class CompanyQueryParams:
    name: str  # required
    location: Optional[str] = None
    businessId: Optional[str] = None
    companyForm: Optional[str] = None
    mainBusinessLine: Optional[str] = None
    registrationDateStart: Optional[str] = None  # Expected in YYYY-MM-DD format
    registrationDateEnd: Optional[str] = None    # Expected in YYYY-MM-DD format
    page: Optional[int] = None

# Setup a very simple in‑memory cache for persistence (mock)
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
          Handle pagination and proper parameter mapping.
    """
    # Simulated response with sample data
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

    # For prototype purposes, simulate a network call for LEI enrichment
    async with aiohttp.ClientSession() as session:
        # TODO: Replace with the actual LEI endpoint
        url = "https://api.example.lei/enrich"
        params = {"businessId": business_id}
        try:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.warning("Non-200 response from LEI service for business_id %s", business_id)
                    # For the prototype, we continue even on error
                # In a real implementation, extract the LEI from the response:
                # data = await resp.json()
                # lei = data.get("lei")
                # Here we simulate a LEI value:
                lei = "LEI" + business_id.replace("-", "")
        except Exception as e:
            logger.error("Error fetching LEI for business_id %s: %s", business_id, e)
            # TODO: Handle exception appropriately
            lei = "UNKNOWN_LEI"
    
    # Cache the result for subsequent calls
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


# The GET /companies endpoint.
# NOTE: For GET requests with query parameters, we use @validate_querystring with our dataclass.
@validate_querystring(CompanyQueryParams)
@app.route("/companies", methods=["GET"])
async def get_companies():
    """
    GET /companies Endpoint.

    Expects query parameters validated by CompanyQueryParams.
    Retrieves companies from the Finnish Companies Registry, filters out inactive companies,
    enriches active companies with LEI and returns a JSON list of results.

    Responses:
      200: JSON list of companies.
      400: Bad Request for missing/invalid parameters.
      500: Internal Server Error for unexpected issues.
    """
    try:
        # Access validated query parameters via the standard request.args interface.
        query_params = request.args.to_dict()
        logger.debug("Received query_params: %s", query_params)
        
        # Fetch companies data from external registry (simulated)
        companies = await fetch_companies_from_registry(query_params)
        
        # Filter out inactive companies
        active_companies = [c for c in companies if c.get("status", "").lower() == "active"]
        logger.debug("Filtered active companies: %s", active_companies)
        
        # Enrich active companies with LEI information by fetching from an external service.
        await enrich_companies_with_lei(active_companies)
        
        # For this prototype, return only active companies.
        return jsonify(active_companies), 200

    except Exception as e:
        logger.exception("Unexpected error in GET /companies")
        return jsonify({"error": "An unexpected error occurred"}), 500


# Example endpoint without validation (if needed).
@app.route("/companies/<string:id>/lei", methods=["GET"])
async def get_company_lei(id: str):
    """
    GET /companies/<id>/lei Endpoint.
    
    Returns the cached LEI for the company with given id.
    No validation is added as per the requirements.
    """
    lei = local_lei_cache.get(id, "LEI_NOT_FOUND")
    return jsonify({"businessId": id, "lei": lei}), 200


# Entry point to run the Quart app
if __name__ == '__main__':
    # Start the Quart server using the given entry point specifications.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
------------------------------------------------------------

Notes:
• The GET /companies endpoint is decorated with @validate_querystring(CompanyQueryParams) to enforce parameter validation.
• We continue using the standard request.args interface to access query data inside the view function.
• POST and PUT endpoints in the future should use @validate_request with an appropriate dataclass for body validation.
• External API URLs and error-handling strategies remain as placeholders to be updated during further development.
• Persistence is simulated via a simple in‑memory cache.
  
This updated code adheres to the guidelines for using quart-schema’s validation decorators while keeping the prototype simple for UX verification and requirement gathering.