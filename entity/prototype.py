Below is the updated prototype.py which now applies request validation for our GET endpoints. In this version the /companies endpoint uses a dataclass (CompaniesQuery) with the minimal required query parameter (“name”) plus an optional “format” parameter; the /companies/search endpoint uses CompaniesSearchQuery that allows for additional filtering. Wherever a placeholder or mock is used, a TODO comment is provided.

------------------------------------------------------------
# prototype.py

from dataclasses import dataclass, asdict
from quart import Quart, request, jsonify, Response
from quart_schema import QuartSchema, validate_querystring  # Using querystring validation for GET endpoints
import aiohttp
import asyncio
import io
import csv

app = Quart(__name__)
QuartSchema(app)  # attach QuartSchema

# In-memory cache placeholder for persistence (mock)
# TODO: Replace with a robust caching/persistence solution if needed
in_memory_cache = {}

# Dataclasses for request validation

@dataclass
class CompaniesQuery:
    name: str
    format: str = "json"  # defaults to JSON if not specified

@dataclass
class CompaniesSearchQuery:
    name: str
    format: str = "json"  # defaults to JSON if not specified
    location: str = None
    businessId: str = None
    companyForm: str = None
    # TODO: Add more optional parameters if needed

# Helper function to convert list of dicts to CSV format
def convert_to_csv(data):
    if not data:
        return ""
    
    # Use StringIO for in-memory file representation
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(data[0].keys()))
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()

async def fetch_finland_companies(name: str, extra_params: dict = None):
    """
    Fetch companies from the Finnish Companies Registry API.
    For the prototype we simulate the external API call with a placeholder.
    TODO: Replace the URL and parameters with those of the actual Finnish Companies Registry API.
    """
    base_url = "https://api.fake-finland.com/companies"  # Placeholder URL
    params = {"name": name}
    if extra_params:
        params.update(extra_params)

    # Use aiohttp.ClientSession for HTTP request
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(base_url, params=params, timeout=5) as resp:
                if resp.status != 200:
                    # TODO: Add proper logging/error handling here.
                    return []  # Returning empty list on error for prototype
                data = await resp.json()
                # For prototype: if data is empty, simulate some sample data.
                if not data:
                    data = [
                        {
                            "companyName": "Acme Oy",
                            "businessId": "1234567-8",
                            "companyType": "Ltd.",
                            "registrationDate": "2020-01-15",
                            "status": "Active",
                            "lei": ""  # Placeholder; will be enriched below.
                        },
                        {
                            "companyName": "Beta Oy",
                            "businessId": "8765432-1",
                            "companyType": "Ltd.",
                            "registrationDate": "2018-05-10",
                            "status": "Inactive",
                            "lei": ""
                        }
                    ]
                return data
        except Exception as e:
            # TODO: Add proper error logging/monitoring here.
            print(f"Error fetching Finnish companies: {e}")
            return []

async def fetch_lei_for_company(business_id: str):
    """
    Enriches a company by retrieving its Legal Entity Identifier (LEI).
    For the prototype we simulate the external API call with a placeholder.
    TODO: Replace the URL and logic to call the official LEI registry or another reliable financial data source.
    """
    lei_api_url = "https://api.fake-lei.com/lookup"  # Placeholder URL
    params = {"businessId": business_id}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(lei_api_url, params=params, timeout=5) as resp:
                if resp.status != 200:
                    return "Not Available"
                lei_data = await resp.json()
                # Assume the JSON response includes an 'lei' field if found.
                lei = lei_data.get("lei") or "Not Available"
                return lei
        except Exception as e:
            # TODO: Add proper error logging/monitoring here.
            print(f"Error fetching LEI for businessId {business_id}: {e}")
            return "Not Available"

@app.route("/companies", methods=["GET"])
@validate_querystring(CompaniesQuery)
async def get_companies(query: CompaniesQuery):
    # Retrieve required parameters from validated query object.
    name = query.name
    output_format = query.format.lower() if query.format else "json"
    
    # Fetch companies data from the external Finnish Companies Registry API.
    companies_data = await fetch_finland_companies(name)

    # Filter out inactive companies (FR-2), keeping only those with active status.
    active_companies = [company for company in companies_data if company.get("status", "").lower() == "active"]

    # Enrich companies with LEI data (FR-3)
    for company in active_companies:
        business_id = company.get("businessId")
        if business_id:
            lei = await fetch_lei_for_company(business_id)
            company["lei"] = lei
        else:
            company["lei"] = "Not Available"

    # Determine output format (JSON or CSV) (FR-4)
    if output_format == "csv":
        csv_output = convert_to_csv(active_companies)
        return Response(csv_output, mimetype="text/csv")
    else:
        return jsonify(active_companies)

@app.route("/companies/search", methods=["GET"])
@validate_querystring(CompaniesSearchQuery)
async def search_companies(query: CompaniesSearchQuery):
    # Convert validated dataclass to dict for extra parameters.
    search_params = asdict(query)
    output_format = search_params.pop("format", "json").lower()
    # Use the "name" parameter and any extra parameters provided.
    name = search_params.pop("name")
    
    # Filter out None values from the search parameters.
    extra_params = {k: v for k, v in search_params.items() if v is not None}
    
    # Fetch companies using the provided query parameters.
    companies_data = await fetch_finland_companies(name, extra_params=extra_params)

    # Filter out inactive companies.
    active_companies = [c for c in companies_data if c.get("status", "").lower() == "active"]

    # Enrich companies with LEI data.
    for company in active_companies:
        business_id = company.get("businessId")
        if business_id:
            lei = await fetch_lei_for_company(business_id)
            company["lei"] = lei
        else:
            company["lei"] = "Not Available"

    if output_format == "csv":
        csv_output = convert_to_csv(active_companies)
        return Response(csv_output, mimetype="text/csv")
    else:
        return jsonify(active_companies)

# Entry point for running the app.
if __name__ == '__main__':
    # Using threaded=True per the requirements.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

------------------------------------------------------------

How this prototype works:
1. GET /companies requires a query parameter “name” (validated by CompaniesQuery) and an optional “format” parameter for output type.
2. GET /companies/search uses CompaniesSearchQuery for validation and accepts additional optional parameters such as "location", "businessId", or "companyForm".
3. Both endpoints fetch company data via a simulated external API call; only active companies are retained.
4. Each active company is enriched with a LEI field via a simulated external API call.
5. The output is rendered in JSON (default) or CSV if requested.

Remember: This prototype uses placeholder endpoints and simple in-memory caching. The mock external API calls (and related URLs) must be replaced with concrete implementations as requirements become clearer.