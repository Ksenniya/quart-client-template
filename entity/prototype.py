Below is an example prototype implementation (prototype.py) that uses Quart, QuartSchema, and aiohttp.ClientSession. Note that this is a working prototype with mocks/placeholders where requirements are not fully specified. For example, the filtering criteria and external LEI service logic are simplified, and persistence uses an in‐memory cache.

------------------------------------------------
#!/usr/bin/env python3
import uuid
import asyncio
import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

app = Quart(__name__)
# Initialize QuartSchema
QuartSchema(app)

# Local in-memory cache for search results (mock persistence)
search_results = {}

# Base URL for the Finnish Companies Registry API
PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"

# Placeholder URL for the external LEI service (TODO: update with official/reliable LEI source)
LEI_API_URL = "https://example-lei.service/mock"  # TODO: Replace with actual LEI service URL

async def fetch_companies(params: dict) -> list:
    async with aiohttp.ClientSession() as session:
        async with session.get(PRH_API_BASE, params=params) as resp:
            if resp.status != 200:
                # TODO: improve error handling
                return []
            data = await resp.json()
            # TODO: Adjust parsing according to the actual API response structure.
            # Assuming the response is a dict with a key 'results' containing company list.
            return data.get("results", [])

async def fetch_lei_for_company(company: dict) -> str:
    # Here we call an external LEI service to get the LEI for the given company.
    # For the prototype, we use a mocked call.
    payload = {
        "businessId": company.get("businessId"),
        "companyName": company.get("name")
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(LEI_API_URL, json=payload) as resp:
                if resp.status == 200:
                    lei_data = await resp.json()
                    lei = lei_data.get("lei")
                    if lei:
                        return lei
                # If no LEI found or service did not return it
                return "Not Available"
        except Exception as e:
            # TODO: Add proper logging
            return "Not Available"

def filter_active_companies(companies: list) -> list:
    # Filter out companies that are not active.
    # TODO: Clarify the criteria for a company to be considered active.
    # Here, we assume the API returns a 'status' field and we check for the string "active".
    active_companies = [company for company in companies if company.get("status", "").lower() == "active"]
    return active_companies

def enrich_company(company: dict, lei: str) -> dict:
    # Build the enriched company dict with the required fields.
    return {
        "Company Name": company.get("name"),
        "Business ID": company.get("businessId"),
        "Company Type": company.get("companyType"),
        "Registration Date": company.get("registrationDate"),
        "Status": company.get("status"),
        "LEI": lei
    }

@app.route('/companies/search', methods=['POST'])
async def search_companies():
    # Parse request JSON payload (the input is dynamic, no request validation)
    data = await request.get_json()
    company_name = data.get("companyName")
    location = data.get("location")
    company_form = data.get("companyForm")
    output_format = data.get("outputFormat", "json").lower()

    if not company_name:
        return jsonify({"error": "companyName is required"}), 400

    # Build query parameters for the Finnish Companies API
    params = {"name": company_name}
    if location:
        params["location"] = location
    if company_form:
        params["companyForm"] = company_form

    # Retrieve companies from external API
    companies = await fetch_companies(params)

    # Filter active companies
    active_companies = filter_active_companies(companies)

    enriched_companies = []
    for company in active_companies:
        lei = await fetch_lei_for_company(company)
        enriched_companies.append(enrich_company(company, lei))
    
    # Assemble final output (could be JSON or CSV)
    # For CSV output, we simply return a CSV string (in prototype, using a simplified approach)
    if output_format == "csv":
        # TODO: Use a proper CSV generation library if needed.
        header = "Company Name,Business ID,Company Type,Registration Date,Status,LEI\n"
        csv_rows = []
        for item in enriched_companies:
            row = f"{item.get('Company Name','')},{item.get('Business ID','')},{item.get('Company Type','')},{item.get('Registration Date','')},{item.get('Status','')},{item.get('LEI','')}"
            csv_rows.append(row)
        final_output = header + "\n".join(csv_rows)
    else:
        final_output = {"results": enriched_companies}

    # Generate a unique search ID and store the result in our in-memory cache
    search_id = str(uuid.uuid4())
    search_results[search_id] = final_output

    # Return immediate response containing searchId and result
    return jsonify({"searchId": search_id, "data": final_output})

@app.route('/companies/result/<search_id>', methods=['GET'])
async def get_search_result(search_id: str):
    # Retrieve the result from our in-memory cache.
    result = search_results.get(search_id)
    if not result:
        return jsonify({"error": "result not found"}), 404
    return jsonify(result)

if __name__ == '__main__':
    # Run the app with the provided entry point options.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
------------------------------------------------

The above prototype meets the provided requirements:
1. POST /companies/search performs external API calls (to PRH API and LEI service), does filtering, and performs data enrichment.
2. GET /companies/result/<search_id> returns previously stored results using an in-memory cache.
3. Mocks and TODO comments indicate missing or unclear parts (e.g., external LEI endpoint, active company criteria, proper CSV implementation).

This solution is intended to verify the UX and expose gaps in the requirements for further refinement.