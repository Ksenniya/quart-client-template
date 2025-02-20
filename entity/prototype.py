Below is the revised prototype.py file with added request validations using quart-schema decorators. Note that for GET requests with query parameters we now use @validate_querystring, and for endpoints that do not require request validation (like the LEI enrichment endpoint) no decorator is added. In this example, we define a dataclass for the query parameters for the /companies endpoint.

------------------------------------------------------------
#!/usr/bin/env python3
"""
Prototype implementation for Finnish Companies Data Retrieval and Enrichment Application.

Endpoints:
1. GET /companies?name=<company_name>
   • Calls an external Finnish Companies Registry API to get company info.
   • Filters out companies that are not active.
   • Caches retrieved companies in memory for subsequent LEI lookup.
   • Validates the query parameters using a dataclass and the @validate_querystring decorator.

2. GET /companies/<id>/lei
   • Uses the in‑memory cache to ensure the company exists.
   • Calls an external LEI API to enrich the company data.
   • Returns the LEI or "Not Available" if not found.

Notes:
• HTTP calls are made with aiohttp.ClientSession.
• The Quart framework is used with QuartSchema.
• Persistence is mocked using a local dictionary.
• Any unclear/external details are marked with TODO comments.
"""

import asyncio
from dataclasses import dataclass
from quart import Quart, request, jsonify, abort, Response
from quart_schema import QuartSchema, validate_querystring  # Import validation functions
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # Initialize Quart Schema

# In-memory cache for companies: key = company id, value = company data dict
companies_cache = {}

# TODO: Replace these URLs with actual endpoints.
COMPANY_REGISTRY_API_URL = "https://api.finnishcompanies.example.com/companies?name="
LEI_API_URL = "https://api.lei.example.com/lei/"  # e.g., LEI API expects: LEI_API_URL + <business_id>

# Dataclass to validate query parameters for GET /companies request
@dataclass
class CompanyQuery:
    name: str  # must be provided as query parameter

# Utility function to simulate filtering active companies.
def filter_active_companies(companies):
    # Assume each company dict contains "status" which is "Active" or "Inactive"
    return [company for company in companies if company.get("status", "").lower() == "active"]

@app.route('/companies', methods=['GET'])
@validate_querystring(CompanyQuery)
async def get_companies(data: CompanyQuery):
    # The query parameter 'name' is now validated and passed as 'data'
    company_name = data.name

    # Use aiohttp client to call external Finnish Companies Registry API
    async with aiohttp.ClientSession() as session:
        try:
            query_url = f"{COMPANY_REGISTRY_API_URL}{company_name}"
            async with session.get(query_url) as resp:
                # TODO: Check for rate limiting responses (429) and handle them appropriately.
                if resp.status == 429:
                    return Response("Rate limit exceeded. Try again later.", status=429)
                elif resp.status != 200:
                    # Log error etc. Here we simply return a 500.
                    return jsonify({"error": "Error retrieving companies from registry"}), 500

                # Expect external API to return a JSON array of companies.
                external_companies = await resp.json()

        except Exception as e:
            # For prototype, return a generic error.
            return jsonify({"error": f"External API call failed: {str(e)}"}), 500

    # TODO: Validate external_companies structure. For now, we assume a list of dicts like:
    # { "id": "<id>", "name": "<company name>", "business_id": "<business id>",
    #   "company_type": "<type>", "registration_date": "YYYY-MM-DD", "status": "Active" or "Inactive" }
    active_companies = filter_active_companies(external_companies)

    # Cache active companies by id for later LEI enrichment lookup.
    for company in active_companies:
        companies_cache[company["id"]] = company

    # Return the active companies.
    return jsonify(active_companies), 200

@app.route('/companies/<string:company_id>/lei', methods=['GET'])
async def get_company_lei(company_id):
    # Check if company exists in our local cache
    if company_id not in companies_cache:
        return jsonify({"error": "Company not found"}), 404

    # Retrieve company details
    company = companies_cache[company_id]
    business_id = company.get("business_id")
    if not business_id:
        # This should not happen, but theoretically, if business_id is missing.
        return jsonify({"lei": "Not Available"}), 200

    # Use aiohttp client to call an external LEI API
    async with aiohttp.ClientSession() as session:
        try:
            lei_url = f"{LEI_API_URL}{business_id}"
            async with session.get(lei_url) as resp:
                if resp.status == 200:
                    lei_data = await resp.json()
                    # TODO: Extract the LEI from lei_data based on the real API schema.
                    lei = lei_data.get("lei", "Not Available")
                elif resp.status == 404:
                    lei = "Not Available"
                else:
                    # On any other error, return "Not Available", but log the error in a real implementation.
                    lei = "Not Available"
        except Exception as e:
            # For the prototype, log exception if needed and return "Not Available".
            lei = "Not Available"

    # Return the LEI information to the client.
    return jsonify({"lei": lei}), 200

if __name__ == '__main__':
    # The specified entry point.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

------------------------------------------------------------

Explanation of key updates:
• Added a dataclass (CompanyQuery) for validating the GET request’s query parameter using @validate_querystring.
• The /companies endpoint now accepts a validated input parameter (data: CompanyQuery), ensuring only requests with a valid 'name' parameter are processed.
• The /companies/<id>/lei endpoint remains unvalidated since it does not require request parameters.
• TODO comments remain where integration details (external API response parsing, rate limit handling, etc.) are to be filled in a production-ready solution.

This updated prototype should now conform to the quart-schema validation examples provided while maintaining the intended user experience.