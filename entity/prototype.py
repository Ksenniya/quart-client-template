Below is a working prototype (prototype.py) that implements the endpoints as defined. Note that many parts (such as data structure details, external LEI API, and persistence) are simulated with placeholders and include TODO comments for further refinement. You can run this prototype using Quart with the entry‐point configuration specified.

--------------------------------------------------
#!/usr/bin/env python3
"""
prototype.py

A working prototype for Finnish Companies Data Retrieval and Enrichment Application.
This prototype uses the PRH avoindata API for company data and simulates LEI enrichment.
External HTTP calls are made using aiohttp. Persistence is simulated via a local in‐memory cache.
"""

import asyncio
import csv
import io
import logging

from quart import Quart, request, jsonify, Response
from quart_schema import QuartSchema

import aiohttp

app = Quart(__name__)
QuartSchema(app)  # enable QuartSchema (no request validation since data is dynamic)

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory cache for LEI data (mock persistence)
LEI_CACHE = {}

# Base URL for the Finnish Companies Registry API (PRH avoindata API)
FINNISH_REGISTRY_BASE_URL = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"


async def fetch_external_companies(params: dict) -> dict:
    """Fetch company data from the Finnish Companies Registry external API.
    
    Args:
        params (dict): Query parameters for the external API.
    
    Returns:
        dict: Parsed JSON response from the external API.
    
    TODO: Adjust the response parsing if the external API returns a structure
          different from what is assumed here.
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(FINNISH_REGISTRY_BASE_URL, params=params) as resp:
                if resp.status != 200:
                    logger.error("Error fetching companies: Status %s", resp.status)
                    # TODO: More sophisticated error handling can be implemented here.
                    return {}
                data = await resp.json()
                return data
        except Exception as e:
            logger.exception("Exception during external API call: %s", e)
            # TODO: Return an error structure or raise a proper HTTP exception.
            return {}


async def simulate_fetch_lei(business_id: str) -> str:
    """Simulate fetching a LEI for a given business_id.
    
    In a full implementation, this function would query an external LEI registry.
    Here, we simulate as follows:
      - If the LEI is already in our cache, return it.
      - Otherwise, if the external service (simulated) “finds” the LEI, we cache and return it.
      - Otherwise, return 'Not Available'.
    
    TODO: Replace with actual logic for LEI enrichment.
    """
    # Check local cache first
    if business_id in LEI_CACHE:
        return LEI_CACHE[business_id]

    # Simulated external LEI lookup:
    # For the sake of this prototype, we assume that companies with even last digit get a LEI.
    try:
        if business_id and business_id[-1].isdigit() and int(business_id[-1]) % 2 == 0:
            lei = f"LEI{business_id}"
        else:
            lei = "Not Available"
    except Exception:
        lei = "Not Available"
    
    # Cache the result for future calls
    LEI_CACHE[business_id] = lei
    return lei


def filter_active_companies(companies: dict) -> list:
    """Filter out inactive companies and retain only the active ones.
    
    Assumes that each company record has a 'status' field. Also, if there are multiple names,
    only active names should be retained.
    
    TODO: Adjust filtering logic based on the actual structure of the external API response.
    """
    active_companies = []
    # Assume that the companies are under a key named 'results' (this might need adjusting)
    for company in companies.get("results", []):
        # Determine if company is active.
        # Here, we check if the 'status' key is present and equals "Active".
        if company.get("status", "").lower() == "active":
            # If there are multiple names/records, choose the active ones.
            # TODO: Implement detailed logic if the structure contains multiple name entries.
            active_companies.append(company)
        else:
            logger.info("Filtered out inactive company: %s", company.get("businessId"))
    return active_companies


def format_as_csv(data: list) -> Response:
    """Format the final data as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    # Write CSV header as specified: Company Name, Business ID, Company Type, Registration Date, Status, LEI
    header = ["Company Name", "Business ID", "Company Type", "Registration Date", "Status", "LEI"]
    writer.writerow(header)
    for record in data:
        writer.writerow([
            record.get("companyName", ""),
            record.get("businessId", ""),
            record.get("companyType", ""),
            record.get("registrationDate", ""),
            record.get("status", ""),
            record.get("lei", ""),
        ])
    response = Response(output.getvalue(), mimetype="text/csv")
    return response


@app.route("/companies", methods=["GET"])
async def get_companies():
    """Retrieve a list of companies based on search criteria, filter inactive ones,
    and enrich active company data with LEI."""
    # Get query parameters from the request
    query_params = dict(request.args)

    # Allow user to specify desired output format (default to JSON)
    output_format = query_params.pop("format", "json").lower()

    logger.info("Received /companies request with params: %s", query_params)

    # Call external Finnish Companies Registry API (using aiohttp)
    external_data = await fetch_external_companies(query_params)

    # Filter out inactive companies
    active_companies = filter_active_companies(external_data)

    # Enrich each active company with LEI.
    # Here we use asyncio.gather to run LEI lookups concurrently.
    tasks = []
    for company in active_companies:
        business_id = company.get("businessId", "")
        # Save the task for LEI lookup.
        tasks.append(simulate_fetch_lei(business_id))
    
    lei_results = await asyncio.gather(*tasks)

    # Attach the LEI to each company in the final response.
    enriched_companies = []
    for company, lei in zip(active_companies, lei_results):
        # Map the company fields to our standardized output.
        enriched_company = {
            "companyName": company.get("name", "N/A"),  # TODO: Adjust the key if external API uses a different one.
            "businessId": company.get("businessId", "N/A"),
            "companyType": company.get("companyForm", "N/A"),  # Assuming field "companyForm" holds the type.
            "registrationDate": company.get("registrationDate", "N/A"),
            "status": company.get("status", "N/A"),
            "lei": lei,
        }
        enriched_companies.append(enriched_company)

    if output_format == "csv":
        return format_as_csv(enriched_companies)
    
    # Default JSON output
    return jsonify(enriched_companies)


@app.route("/companies/<business_id>/lei", methods=["GET"])
async def get_company_lei(business_id: str):
    """Retrieve the LEI information for a given company by its Business ID."""
    logger.info("Received LEI request for business_id: %s", business_id)
    
    lei = await simulate_fetch_lei(business_id)
    if lei == "Not Available":
        # Return HTTP 404 if LEI not found.
        return jsonify({"error": "LEI not found"}), 404
    
    return jsonify({"lei": lei})


if __name__ == '__main__':
    # Run Quart with the specified entry point configuration.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

--------------------------------------------------

Notes:
1. The external companies API response is assumed to have a key "results" containing a list
   of company dictionaries. Adjust the JSON navigation as needed.
2. In simulate_fetch_lei, the logic to determine whether a company gets a LEI is a simple placeholder.
3. Logging is used to help track filtering and errors.
4. The CSV output uses Python’s csv module, and the content type is set to text/csv.
5. Persistence and caching are done with a local dictionary (LEI_CACHE) only.

This prototype should let you verify the basic UX and identify any missing requirements before a more robust implementation.