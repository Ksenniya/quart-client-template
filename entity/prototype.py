from dataclasses import dataclass
from typing import Optional, List
import asyncio
import uuid
import csv
from io import StringIO

from quart import Quart, request, jsonify, Response
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring
import aiohttp

# Setup in-memory cache (mock persistence)
SEARCH_CACHE = {}

app = Quart(__name__)
QuartSchema(app)

# Data Models for validation

@dataclass
class SearchCriteria:
    companyName: str
    registrationDateStart: Optional[str] = None  # Expect format "yyyy-mm-dd"
    registrationDateEnd: Optional[str] = None    # Expect format "yyyy-mm-dd"

@dataclass
class SearchResponse:
    searchId: str
    status: str

@dataclass
class ResultsQuery:
    format: str = "json"  # Allowed values: "json" or "csv"

# Constants for external API endpoints
PRH_API_URL = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
# TODO: Replace with the actual LEI data provider endpoint if available.
LEI_API_URL = "https://mock-lei-provider.com/api/lei"  # This is a mock placeholder

async def fetch_companies_from_prh(params: dict) -> List[dict]:
    """Fetch companies from the Finnish Companies Registry (PRH) API."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(PRH_API_URL, params=params) as response:
                if response.status != 200:
                    # TODO: Enhance error handling (e.g., logging, retries)
                    return []
                data = await response.json()
                # Assuming the API returns a list under the key "results" (adjust if needed)
                companies = data.get("results", [])
                return companies
        except Exception as e:
            # TODO: Log exception details
            return []

async def fetch_lei_for_company(business_id: str) -> str:
    """Fetch the Legal Entity Identifier (LEI) for a given company.
       In this prototype, this is a mock call returning a dummy LEI if business_id is provided.
    """
    async with aiohttp.ClientSession() as session:
        try:
            params = {"businessId": business_id}  # Simulated query parameter
            async with session.get(LEI_API_URL, params=params) as response:
                if response.status == 200:
                    lei_data = await response.json()
                    lei = lei_data.get("lei", "Not Available")
                    return lei
                else:
                    return "Not Available"
        except Exception as e:
            # TODO: Log exception details and handle errors properly
            return "Not Available"

@validate_request(SearchCriteria)
@validate_response(SearchResponse, 200)
@app.route("/api/companies/search", methods=["POST"])
async def search_companies(data: SearchCriteria):
    """
    POST endpoint to search companies by criteria.
    It calls the external PRH API, filters out inactive companies, enriches data with LEI,
    and stores the final result in a local cache.
    """
    # Build parameters for PRH API using the validated data
    prh_params = {"name": data.companyName}
    if data.registrationDateStart:
        prh_params["registrationDateStart"] = data.registrationDateStart
    if data.registrationDateEnd:
        prh_params["registrationDateEnd"] = data.registrationDateEnd
    # TODO: Add processing of additional parameters if needed.

    companies = await fetch_companies_from_prh(prh_params)

    # Filter out inactive companies.
    # Assuming each company record has a "status" key (active if "active")
    active_companies = [comp for comp in companies if comp.get("status", "").lower() == "active"]
    # TODO: Enhance filtering logic if companies have multiple names/statuses.

    # Enrich each active company with LEI data.
    enriched_companies = []
    for comp in active_companies:
        business_id = comp.get("businessId")
        lei = "Not Available"
        if business_id:
            lei = await fetch_lei_for_company(business_id)
        # Build the enriched company record in the required format.
        enriched_companies.append({
            "companyName": comp.get("name", "Unknown"),
            "businessId": business_id or "Unknown",
            "companyType": comp.get("companyForm", "Unknown"),
            "registrationDate": comp.get("registrationDate", "Unknown"),
            "status": comp.get("status", "Unknown"),
            "lei": lei
        })

    # Generate a unique searchId and store results in the in-memory cache.
    search_id = str(uuid.uuid4())
    SEARCH_CACHE[search_id] = enriched_companies

    # Response with searchId and current status
    return SearchResponse(searchId=search_id, status="completed")

@validate_querystring(ResultsQuery)
@app.route("/api/companies/results/<search_id>", methods=["GET"])
async def get_search_results(search_id):
    """
    GET endpoint to retrieve the enriched company search results stored in memory.
    Supports JSON or CSV output based on query parameter.
    """
    results = SEARCH_CACHE.get(search_id)
    if results is None:
        return jsonify({"error": "No result found for this searchId"}), 404

    # Validate query parameter "format" using request.args manually as validated query is not passed to function.
    resp_format = request.args.get("format", "json").lower()
    if resp_format == "csv":
        output = StringIO()
        fieldnames = ["companyName", "businessId", "companyType", "registrationDate", "status", "lei"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)
        return Response(output.getvalue(), mimetype="text/csv")
    else:
        return jsonify({"results": results})

@app.route("/api/health", methods=["GET"])
async def health_check():
    """A simple health check endpoint."""
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)