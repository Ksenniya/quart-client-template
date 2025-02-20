Below is the updated prototype.py file. Note that the two main endpoints (GET /companies and GET /companies/<id>/lei) are not decorated with validate_request because the decorator isn’t applicable for GET methods. For demonstration purposes we’ve also added a dummy POST endpoint (/test) that uses @validate_request and @validate_response, which follows the quart-schema example you provided.

------------------------------------------------------------
#!/usr/bin/env python3
"""
prototype.py

A working prototype for the Finnish Companies Data Retrieval and Enrichment Application.
This code uses Quart as the API framework with QuartSchema along with aiohttp.ClientSession for HTTP calls.
Persistence is only simulated via an in‐memory local cache.
"""

import asyncio
from dataclasses import dataclass
import aiohttp
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response

# Create our Quart application and add QuartSchema (single line as specified)
app = Quart(__name__)
QuartSchema(app)

# Global in-memory cache for company data keyed by businessId.
COMPANIES_CACHE = {}

# Dummy external API URLs (placeholders)
PRH_AVOINDATA_API_URL = "https://api.avoindata.prh.fi"  # TODO: set correct endpoint if available
LEI_API_URL = "https://api.lei.example.com"  # TODO: set correct LEI API endpoint if available


async def query_prh_api(params: dict) -> list:
    """
    Queries the PRH Avoindata API with given parameters and returns a list of companies.
    For the prototype we simulate the response.

    :param params: Dictionary containing search parameters (e.g., name, location, businessId, companyForm, page)
    :return: List of company dictionaries.
    """
    # TODO: Replace with an actual HTTP request to PRH Avoindata API once details are finalized.
    # For now, we return a dummy list of companies; note that inactive companies are present.
    dummy_companies = [
        {
            "companyName": "Example Company",
            "businessId": "1234567-8",
            "companyType": "OY",
            "registrationDate": "2020-01-01",
            "status": "Active",
        },
        {
            "companyName": "Inactive Company",
            "businessId": "9876543-2",
            "companyType": "OY",
            "registrationDate": "2019-05-01",
            "status": "Inactive",
        },
        {
            "companyName": "Another Active Company",
            "businessId": "5555555-5",
            "companyType": "OY",
            "registrationDate": "2021-06-15",
            "status": "Active",
        },
    ]
    # Simulate network delay
    await asyncio.sleep(0.1)
    return dummy_companies


async def fetch_lei_for_company(business_id: str) -> str:
    """
    Retrieves the Legal Entity Identifier (LEI) for a given company/business id.
    For now, this function uses a mocked response.

    :param business_id: The identifier for the company.
    :return: A string representing the LEI or "Not Available" if not found.
    """
    # TODO: Replace with actual call to external LEI API using aiohttp.ClientSession when available.
    await asyncio.sleep(0.05)  # simulate API latency

    # Simple mock: if the businessId ends with an 8 or 5, assume we have an LEI.
    if business_id.endswith(("8", "5")):
        return "LEI-EXAMPLE"
    return "Not Available"


@app.route("/companies", methods=["GET"])
async def get_companies():
    """
    GET /companies endpoint.
    Requires a query parameter "name" (company name/partial name). It can also accept location, businessId,
    companyForm, and page.
    
    It queries the PRH Avoindata API, filters out companies with an inactive status,
    enriches each active company record with LEI data, and returns the results.
    """
    query_params = request.args
    name = query_params.get("name")
    
    # Check that the required "name" parameter is provided.
    if not name:
        return jsonify({"error": "Invalid parameters: 'name' is required"}), 400

    # Build search parameters for the external API.
    search_params = {
        "name": name,
        "location": query_params.get("location"),
        "businessId": query_params.get("businessId"),
        "companyForm": query_params.get("companyForm"),
        "page": query_params.get("page"),
    }
    
    # Query the external PRH API (simulated here)
    companies_data = await query_prh_api(search_params)
    
    # Filter out inactive companies.
    active_companies = [company for company in companies_data if company.get("status") == "Active"]
    
    # Enrich each company with LEI data.
    enriched_companies = []
    for company in active_companies:
        business_id = company.get("businessId")
        lei = await fetch_lei_for_company(business_id)
        enriched_company = {
            "companyName": company.get("companyName"),
            "businessId": business_id,
            "companyType": company.get("companyType"),
            "registrationDate": company.get("registrationDate"),
            "status": company.get("status"),
            "lei": lei,
        }
        enriched_companies.append(enriched_company)
        # Update local cache for later LEI lookups.
        COMPANIES_CACHE[business_id] = enriched_company

    # TODO: Handle pagination if the results are very large.
    return jsonify({"companies": enriched_companies}), 200


@app.route("/companies/<string:business_id>/lei", methods=["GET"])
async def get_company_lei(business_id: str):
    """
    GET /companies/{id}/lei endpoint.
    Retrieves the LEI for a specific company.
    
    - If the company exists in the local cache, returns its LEI.
    - Otherwise, it tries to fetch the LEI (using the same mocked call) and updates the cache.
    - If the company cannot be found, returns a 404.
    """
    company = COMPANIES_CACHE.get(business_id)
    if company is None:
        # Optionally, try to fetch the company details from the external API.
        # For the prototype, we consider missing cache as a 404.
        return jsonify({"error": "Company not found"}), 404

    lei = company.get("lei")
    if not lei or lei == "Not Available":
        # Optionally, re-fetch LEI, but for the prototype we return as is.
        lei = await fetch_lei_for_company(business_id)
        company["lei"] = lei
        COMPANIES_CACHE[business_id] = company

    return jsonify({"lei": lei}), 200


# --------------------------------------------------------------------
# Dummy POST endpoint to demonstrate usage of @validate_request
# and @validate_response from quart-schema.
# This is added solely for illustration and testing purposes.
# --------------------------------------------------------------------
@dataclass
class TestData:
    example_field: str  # Use only a primitive type per spec


@app.route("/test", methods=["POST"])
@validate_request(TestData)
@validate_response(TestData, 201)
async def test_endpoint(data: TestData):
    """
    Echo endpoint for testing validate_request and validate_response.
    Expects a JSON body with an "example_field" key.
    """
    # For demonstration purposes, simply echo back the received data.
    return jsonify(data.__dict__), 201


if __name__ == "__main__":
    # Run the application using the specified entry point.
    # Note: threaded=True is typically not recommended in production but is allowed for this prototype.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
------------------------------------------------------------

Notes:
• The GET endpoints remain undecorated because validate_request isn’t applicable for GET.
• A dummy POST endpoint (/test) is included to demonstrate how to use @validate_request and @validate_response per the quart-schema example.
• External API calls and persistence are mocked/simulated with TODO comments indicating where a complete implementation is needed.
• This prototype serves as a proof of concept for verifying the user experience (UX) and identifying any gaps in the requirements.