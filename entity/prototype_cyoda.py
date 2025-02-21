Below is the updated code. In this version, all direct accesses to the in‑memory local cache (local_lei_cache) have been removed. Instead, for caching and retrieving a company’s LEI we now rely on the external service (entity_service) by using its get_item and add_item functions. In addition, the Quart startup hook has been added at the top to initialize Cyoda at start‑up. (Other business logic, validations, external API calls, etc., remain unchanged.)

Make sure you have the proper definitions for cyoda_token and ENTITY_VERSION in scope.

------------------------------------------------------------
#!/usr/bin/env python3
"""
Prototype for Finnish Companies Data Retrieval and Enrichment Application.

This prototype exposes a GET /companies endpoint which:
  • Searches companies by name (and optional filters)
  • Filters out inactive companies
  • Enriches each active company with its Legal Entity Identifier (LEI)

External API calls are currently mocked using aiohttp.ClientSession with placeholder URLs.
Persistence is now managed by an external service (entity_service) instead of a local
in‑memory cache.
"""

import asyncio
import aiohttp
import logging
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_querystring  # For GET requests, use validate_querystring
from dataclasses import dataclass
from typing import Optional

# Import the external cache service and initialization functions/values.
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

# Define a constant for the entity version (assumed to be defined somewhere)
ENTITY_VERSION = "1.0"

# Create the Quart app instance and initialize QuartSchema
app = Quart(__name__)
QuartSchema(app)

# Register startup hook to initialize Cyoda.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

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
    The caching is now handled by the external entity_service.

    TODO: Replace the URL with the actual LEI enrichment service endpoint.
    """
    # Try to get the cached LEI from the external cache service.
    try:
        item = await entity_service.get_item(
            token=cyoda_token,
            entity_model="lei_cache",  # Name of the entity type for LEI caching.
            entity_version=ENTITY_VERSION,
            technical_id=business_id
        )
        if item and "lei" in item:
            logger.debug("Returning cached LEI for business_id %s", business_id)
            return item["lei"]
    except Exception as e:
        logger.debug("No cached LEI found for business_id %s: %s", business_id, e)

    # For prototype purposes, simulate a network call for LEI enrichment.
    async with aiohttp.ClientSession() as session:
        # TODO: Replace with the actual LEI endpoint.
        url = "https://api.example.lei/enrich"
        params = {"businessId": business_id}
        try:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.warning("Non-200 response from LEI service for business_id %s", business_id)
                # In a real implementation, extract the LEI from the response:
                # data = await resp.json()
                # lei = data.get("lei")
                # Here we simulate a LEI value:
                lei = "LEI" + business_id.replace("-", "")
        except Exception as e:
            logger.error("Error fetching LEI for business_id %s: %s", business_id, e)
            lei = "UNKNOWN_LEI"
    
    # Cache the fetched LEI using the external entity service.
    data = {"technical_id": business_id, "lei": lei}
    try:
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="lei_cache",  # Use same model name for storing LEI info.
            entity_version=ENTITY_VERSION,
            entity=data
        )
        logger.debug("Caching LEI for business_id %s: %s", business_id, lei)
    except Exception as e:
        logger.error("Error caching LEI for business_id %s: %s", business_id, e)
    
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

# Example endpoint to get the LEI for a company by its business id.
@app.route("/companies/<string:id>/lei", methods=["GET"])
async def get_company_lei(id: str):
    """
    GET /companies/<id>/lei Endpoint.
    
    Returns the cached LEI for the company with the given id
    using the external entity_service cache.
    """
    try:
        item = await entity_service.get_item(
            token=cyoda_token,
            entity_model="lei_cache",  # Same model as used for caching in get_lei.
            entity_version=ENTITY_VERSION,
            technical_id=id
        )
        lei = item.get("lei") if item else "LEI_NOT_FOUND"
    except Exception as e:
        logger.error("Error retrieving LEI for company id %s: %s", id, e)
        lei = "LEI_NOT_FOUND"
    return jsonify({"businessId": id, "lei": lei}), 200

# Entry point to run the Quart app
if __name__ == '__main__':
    # Start the Quart server using the given entry point specifications.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
------------------------------------------------------------

Notes:
• The GET /companies endpoint remains unchanged in its core business logic; only the in‑memory cache operations now call the external entity_service.
• The get_lei function first attempts to retrieve the LEI from the external cache; if not available, it simulates a network call to enrich the LEI, then stores it externally.
• The startup code initializes Cyoda before serving requests.
• If additional caching operations for other entities are needed, similar replacement calls to entity_service (using add_item, get_item, etc.) should be applied.
• The entity model name "lei_cache" is used to identify our cached LEI data.
  
This refactoring preserves the endpoint routes and business logic while replacing local cache interactions with calls to an external persistence service.