Below is an updated prototype.py file that includes request validation using the quart-schema decorators. In this example we define dataclasses for the querystring for our GET endpoints. (Note that POST/PUT endpoints would use @validate_request, but our prototype only includes GET endpoints.) Review the TODO comments for any mocked or placeholder implementations.

────────────────────────────────────────────────────────────
#!/usr/bin/env python3
"""
Prototype for the Finnish Companies Data Retrieval and Enrichment Application.

Endpoints:
  • GET /companies
    - Searches for companies using query parameters (name, location, businessId, companyForm).
    - Filters out inactive companies.
    - If no LEI is defined, sets it to "Not Available".
    - Supports output formats: JSON (default) or CSV (when format=csv is provided)

  • GET /companies/lei
    - Retrieves/enriches LEI for a company using its businessId.
    - If the company exists in the local cache and already has a LEI, returns that.
    - Otherwise, makes an asynchronous GET request to an external LEI API.
      (This external call is mocked with a placeholder URL; see TODO comments.)

Usage:
  Run this file directly to launch the Quart application.
"""

import io
import csv
import aiohttp
from dataclasses import dataclass
from quart import Quart, request, jsonify, Response
from quart_schema import QuartSchema, validate_querystring  # Using validate_querystring for GET endpoints

app = Quart(__name__)
# Initialize Quart Schema for request/response validation
QuartSchema(app)

# Define dataclasses for querystring validation.
# Use only primitive types and provide default values when appropriate.
@dataclass
class CompaniesQuery:
    name: str = None
    location: str = None
    businessId: str = None
    companyForm: str = None
    format: str = "json"  # Default output format is JSON

@dataclass
class LeiQuery:
    businessId: str  # businessId is required for LEI lookup

# In-memory local cache (mock persistence) for companies
companies_data = [
    {
        "companyName": "Example Company",
        "businessId": "1234567-8",
        "companyType": "OY",
        "registrationDate": "2020-01-01",
        "status": "Active",
        "lei": "LEI123456789",
        "location": "Helsinki"  # Extra field available for filtering by location
    },
    {
        "companyName": "Inactive Company",
        "businessId": "9876543-2",
        "companyType": "OY",
        "registrationDate": "2019-05-05",
        "status": "Inactive",
        "lei": None,
        "location": "Espoo"
    }
]

@validate_querystring(CompaniesQuery)  # This decorator validates querystring parameters before route handling.
@app.route("/companies", methods=["GET"])
async def get_companies():
    """
    GET /companies
     - Search companies by optional query parameters (name, location, businessId, companyForm).
     - Only companies with status "Active" are returned.
     - Output format is determined by the "format" querystring parameter:
         • JSON (default) or CSV (if format=csv)
    """
    # Use standard approach to access query parameters.
    name = request.args.get("name")
    location = request.args.get("location")
    business_id = request.args.get("businessId")
    company_form = request.args.get("companyForm")
    output_format = (request.args.get("format") or "json").lower()

    # Filter companies based on search criteria
    filtered_companies = []
    for comp in companies_data:
        # Only include active companies (filter out inactive ones)
        if comp.get("status", "").lower() != "active":
            continue
        if name and name.lower() not in comp.get("companyName", "").lower():
            continue
        if location and location.lower() not in comp.get("location", "").lower():
            continue
        if business_id and business_id != comp.get("businessId"):
            continue
        if company_form and company_form.lower() not in comp.get("companyType", "").lower():
            continue

        # For companies without LEI, mark as "Not Available"
        comp_copy = comp.copy()
        if not comp_copy.get("lei"):
            comp_copy["lei"] = "Not Available"
        filtered_companies.append(comp_copy)

    if not filtered_companies:
        return jsonify({"error": "No companies found"}), 404

    # Return results in the selected output format (JSON is default)
    if output_format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=filtered_companies[0].keys())
        writer.writeheader()
        for comp in filtered_companies:
            writer.writerow(comp)
        return Response(output.getvalue(), mimetype="text/csv")
    else:
        return jsonify({"companies": filtered_companies})

@validate_querystring(LeiQuery)  # Validates that businessId is provided and is a string.
@app.route("/companies/lei", methods=["GET"])
async def get_company_lei():
    """
    GET /companies/lei
      - Enrich company data by retrieving its Legal Entity Identifier (LEI)
      - Uses businessId as parameter for lookup.
      - If LEI exists in the local cache, returns that value;
        otherwise, calls an external (mocked) API to lookup the LEI.
    """
    business_id = request.args.get("businessId")
    if not business_id:
        return jsonify({"error": "Missing businessId parameter"}), 400

    # Lookup the company in our local cache
    company = next((c for c in companies_data if c.get("businessId") == business_id), None)
    if not company:
        return jsonify({"error": "Company not found"}), 404

    lei_value = company.get("lei")
    if lei_value:
        return jsonify({"lei": lei_value})
    else:
        # TODO: Replace the placeholder URL with the actual external LEI API endpoint and implement robust error handling.
        external_api_url = f"http://external-lei-api.com/lookup?businessId={business_id}"  # Placeholder URL for external LEI lookup
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(external_api_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        lei = data.get("lei", "Not Available")
                        # Update local cache for future requests (mock persistence)
                        company["lei"] = lei
                        return jsonify({"lei": lei})
                    else:
                        return jsonify({"lei": "Not Available"}), 200
            except Exception as e:
                # TODO: Log the exception properly. For now, simply return "Not Available" if the external call fails.
                return jsonify({"lei": "Not Available"}), 200

if __name__ == '__main__':
    # Run the Quart application.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
────────────────────────────────────────────────────────────

Notes:
• The dataclasses CompaniesQuery and LeiQuery are used for validating GET request query parameters.
• For GET requests, we rely on validate_querystring (which must be the first decorator) and then access parameters via request.args.
• Persistence remains a local in-memory cache.
• External API calls use aiohttp.ClientSession and are currently mocked with a placeholder URL.
• TODO comments indicate where a real external API endpoint and proper logging/error handling must be integrated.

This revised prototype should now better illustrate how to incorporate request validation using quart-schema while still verifying UX before a full implementation.