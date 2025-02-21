Below is one possible refactored version of prototype.py. In this version the local in‑memory list (companies_data) has been removed and all reads and writes are accomplished via the external entity_service calls. (Since the allowed functions don’t include creation endpoints, note that no POST endpoint is provided here—but for endpoints that do add items you would use entity_service.add_item and then include the returned id in the response.) 

In addition, the new startup code is added and ENTITY_VERSION is imported as required. (For any functionality that can’t be mapped to a permitted call—for example, if more complex filtering were needed—the previous behavior is maintained after retrieving the “full list” from the external service.) 

Below is the complete refactored code:

------------------------------------------------------------
#!/usr/bin/env python3
"""
Prototype for the Finnish Companies Data Retrieval and Enrichment Application.

Endpoints:
  • GET /companies
    - Searches for companies using query parameters (name, location, businessId, companyForm).
    - Only companies with status "Active" are returned.
    - If no LEI is defined, sets it to "Not Available".
    - Supports output formats: JSON (default) or CSV (when format=csv is provided)

  • GET /companies/lei
    - Retrieves/enriches LEI for a company using its businessId.
    - If the company exists in the external store *and* already has a LEI, returns that.
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

# Import external service functions and supporting variables.
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

app = Quart(__name__)
# Initialize Quart Schema for request/response validation
QuartSchema(app)

# Initialize cyoda before serving.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Define dataclasses for querystring validation.
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

# GET /companies endpoint.
@validate_querystring(CompaniesQuery)  # This decorator validates querystring parameters before route handling.
@app.route("/companies", methods=["GET"])
async def get_companies():
    """
    GET /companies
     - Search companies by optional query parameters (name, location, businessId, companyForm).
     - Only companies with status "Active" are returned.
     - Output format is determined by the "format" querystring parameter:
         • JSON (default) or CSV (if format=csv)
     
    Implementation notes:
      Instead of filtering a local in‑memory collection, we retrieve all companies via
      entity_service.get_items and perform the filtering in this service.
    """
    # Retrieve query parameters.
    name = request.args.get("name")
    location = request.args.get("location")
    business_id = request.args.get("businessId")
    company_form = request.args.get("companyForm")
    output_format = (request.args.get("format") or "json").lower()

    # Get all companies from the external service.
    companies = await entity_service.get_items(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
    )
    if companies is None:
        companies = []  # Just in case

    # Filter companies based on search criteria.
    filtered_companies = []
    for comp in companies:
        # Only include active companies.
        if (comp.get("status") or "").lower() != "active":
            continue
        if name and name.lower() not in (comp.get("companyName") or "").lower():
            continue
        if location and location.lower() not in (comp.get("location") or "").lower():
            continue
        if business_id and business_id != comp.get("businessId"):
            continue
        if company_form and company_form.lower() not in (comp.get("companyType") or "").lower():
            continue

        # For companies without LEI, mark as "Not Available"
        comp_copy = comp.copy()
        if not comp_copy.get("lei"):
            comp_copy["lei"] = "Not Available"
        filtered_companies.append(comp_copy)

    if not filtered_companies:
        return jsonify({"error": "No companies found"}), 404

    # Return results in the selected output format.
    if output_format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=filtered_companies[0].keys())
        writer.writeheader()
        for comp in filtered_companies:
            writer.writerow(comp)
        return Response(output.getvalue(), mimetype="text/csv")
    else:
        return jsonify({"companies": filtered_companies})

# GET /companies/lei endpoint.
@validate_querystring(LeiQuery)  # Validates that businessId is provided and is a string.
@app.route("/companies/lei", methods=["GET"])
async def get_company_lei():
    """
    GET /companies/lei
      - Enrich company data by retrieving its Legal Entity Identifier (LEI)
      - Uses businessId as parameter for lookup.
      - If the company exists in the external store and already has a LEI, returns that value;
        otherwise, calls an external (mocked) API to look up the LEI.
    """
    business_id = request.args.get("businessId")
    if not business_id:
        return jsonify({"error": "Missing businessId parameter"}), 400

    # Retrieve the company using the provided businessId.
    companies_found = await entity_service.get_items_by_condition(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        condition={"businessId": business_id},
    )
    if not companies_found or len(companies_found) == 0:
        return jsonify({"error": "Company not found"}), 404

    # Assume using the first matching record.
    company = companies_found[0]
    lei_value = company.get("lei")
    if lei_value:
        return jsonify({"lei": lei_value})
    else:
        # No LEI available in the record; perform external lookup.
        external_api_url = f"http://external-lei-api.com/lookup?businessId={business_id}"  # Placeholder URL.
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(external_api_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        lei = data.get("lei", "Not Available")
                        # Update the company record with the new LEI.
                        company["lei"] = lei
                        await entity_service.update_item(
                            token=cyoda_token,
                            entity_model="companies",
                            entity_version=ENTITY_VERSION,
                            entity=company,
                            meta={}
                        )
                        return jsonify({"lei": lei})
                    else:
                        return jsonify({"lei": "Not Available"}), 200
            except Exception as e:
                # TODO: Log the exception properly.
                return jsonify({"lei": "Not Available"}), 200

if __name__ == '__main__':
    # Run the Quart application.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

------------------------------------------------------------

Notes on this version:
1. All data retrieval and update calls now use entity_service.get_items, get_items_by_condition, and update_item instead of directly reading/writing a local dictionary.
2. For a creation (POST) endpoint (not provided here), one would call entity_service.add_item(...) and include the returned id in the response so that users can later query the new item by that id.
3. The original business logic (filtering, marking missing LEI as "Not Available", and external API lookup) has been preserved.
4. The startup hook initializes the Cyoda repository using the provided token.

This is one accepted solution; depending on your business needs and the entity_service’s API (synchronous or asynchronous), further adjustments might be necessary.