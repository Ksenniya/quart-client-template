import asyncio
import uuid
from quart import Quart, request, jsonify, Response
from quart_schema import QuartSchema

import aiohttp

# Global in-memory "cache" to store search results (Mock persistence)
SEARCH_CACHE = {}

app = Quart(__name__)
# Enable QuartSchema for potential schema validations (not using @validate_request as data is dynamic)
QuartSchema(app)

# Constants for external API endpoints
PRH_API_URL = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
# TODO: Replace with the actual LEI data provider endpoint if available.
LEI_API_URL = "https://mock-lei-provider.com/api/lei"  # This is a mock placeholder

async def fetch_companies_from_prh(params: dict) -> list:
    """Fetch companies from the Finnish Companies Registry (PRH) API."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(PRH_API_URL, params=params) as response:
                if response.status != 200:
                    # TODO: Enhance error handling as needed.
                    return []
                data = await response.json()
                # Assuming the API returns a list in key 'results' (adjust as per the actual API response)
                companies = data.get("results", [])
                return companies
        except Exception as e:
            # TODO: Log exception details
            return []

async def fetch_lei_for_company(business_id: str) -> str:
    """Fetch the Legal Entity Identifier (LEI) for a given company.
       In this prototype, this is a mock call returning a dummy LEI if business_id is not empty.
    """
    # TODO: Replace this placeholder logic with a real request to a reliable LEI data provider.
    async with aiohttp.ClientSession() as session:
        try:
            # Simulated API call with businessId as query parameter.
            params = {"businessId": business_id}
            async with session.get(LEI_API_URL, params=params) as response:
                if response.status == 200:
                    lei_data = await response.json()
                    lei = lei_data.get("lei", "Not Available")
                    return lei
                else:
                    return "Not Available"
        except Exception as e:
            # TODO: Log exception and handle errors appropriately.
            return "Not Available"

@app.route("/api/companies/search", methods=["POST"])
async def search_companies():
    """
    POST endpoint to search companies by criteria.
    It calls the external PRH API, filters out inactive companies, enriches data with the LEI,
    and stores the final result in a local cache.
    """
    req_data = await request.get_json()
    # Extract search criteria (e.g., companyName, registrationDateStart, registrationDateEnd)
    company_name = req_data.get("companyName")
    if not company_name:
        return jsonify({"error": "companyName is required!"}), 400

    # Build query parameters for PRH API call
    # We only use companyName for this prototype; additional parameters can be added as needed.
    prh_params = {"name": company_name}
    if req_data.get("registrationDateStart"):
        prh_params["registrationDateStart"] = req_data.get("registrationDateStart")
    if req_data.get("registrationDateEnd"):
        prh_params["registrationDateEnd"] = req_data.get("registrationDateEnd")
    # TODO: Add processing of additional parameters if needed.

    companies = await fetch_companies_from_prh(prh_params)

    # Filter out inactive companies.
    # Assuming each company record has a key "status" that indicates if it's active.
    active_companies = [comp for comp in companies if comp.get("status", "").lower() == "active"]
    # TODO: Enhance filtering logic if companies contain multiple names or statuses.

    # Enrich each active company with LEI data.
    enriched_companies = []
    for comp in active_companies:
        business_id = comp.get("businessId")
        lei = "Not Available"
        if business_id:
            lei = await fetch_lei_for_company(business_id)
        # Build the enriched company data in the required output format.
        enriched_companies.append({
            "companyName": comp.get("name", "Unknown"),
            "businessId": business_id or "Unknown",
            "companyType": comp.get("companyForm", "Unknown"),
            "registrationDate": comp.get("registrationDate", "Unknown"),
            "status": comp.get("status", "Unknown"),
            "lei": lei
        })

    # Generate a unique searchId, store the result in local cache.
    search_id = str(uuid.uuid4())
    SEARCH_CACHE[search_id] = enriched_companies

    # Return searchId and status.
    return jsonify({"searchId": search_id, "status": "completed"}), 200

@app.route("/api/companies/results/<search_id>", methods=["GET"])
async def get_search_results(search_id):
    """
    GET endpoint to retrieve the enriched company search results stored in memory.
    Supports JSON output. To support CSV conversion, further implementation would be needed.
    """
    results = SEARCH_CACHE.get(search_id)
    if results is None:
        return jsonify({"error": "No result found for this searchId"}), 404

    # Check if a format is requested via query parameter, default to JSON.
    resp_format = request.args.get("format", "json").lower()
    if resp_format == "csv":
        # Create CSV output.
        # TODO: Enhance CSV formatting based on real output requirements.
        import csv
        from io import StringIO
        output = StringIO()
        fieldnames = ["companyName", "businessId", "companyType", "registrationDate", "status", "lei"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)
        response = Response(output.getvalue(), mimetype="text/csv")
        return response
    else:
        return jsonify({"results": results}), 200

@app.route("/api/health", methods=["GET"])
async def health_check():
    """A simple health check endpoint."""
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

# End of prototype.py

