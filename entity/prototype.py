Below is an example prototype.py file that follows your requirements. This prototype uses aiohttp for external HTTP calls, Quart for routing, and a simple in‑memory cache for jobs. Any external data details are represented by mocks or placeholders with TODO comments.

------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
import json

from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # initialize QuartSchema

# In-memory store for job results; in production this would be replaced by a persistent store.
jobs = {}

# Constants for external API endpoints
PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
# TODO: Replace LEI_API_URL_TEMPLATE with a real endpoint for LEI lookup.
LEI_API_URL_TEMPLATE = "https://api.example.com/lei?businessId={businessId}"


@app.route("/companies/search", methods=["POST"])
async def search_companies():
    data = await request.get_json()

    company_name = data.get("companyName", "").strip()
    if not company_name:
        return jsonify({"error": "Missing required field 'companyName'"}), 400

    page = data.get("page", 1)
    output_format = data.get("outputFormat", "json").lower()
    # Generate a unique job ID and store an initial record.
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.datetime.utcnow().isoformat(),
        "results": None,
    }
    
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, company_name, page, output_format))
    
    return jsonify({"job_id": job_id, "status": "processing"}), 202


@app.route("/companies/results/<job_id>", methods=["GET"])
async def get_results(job_id):
    job = jobs.get(job_id)
    if job is None:
        abort(404, description="Job ID not found")
    
    if job["status"] == "processing":
        return jsonify({"job_id": job_id, "status": "processing"}), 202
    
    # Return final results.
    if job["results"] is None:
        return jsonify({"error": "No results available"}), 500

    # Depending on output_format, the response could be json or csv.
    # For this prototype we return JSON regardless.
    return jsonify({
        "job_id": job_id,
        "status": "completed",
        "results": job["results"],
    }), 200


async def process_entity(job_id, company_name, page, output_format):
    results = []
    try:
        async with aiohttp.ClientSession() as session:
            # Build query parameters for the PRH API
            params = {
                "name": company_name,
                "page": page
            }
            async with session.get(PRH_API_BASE, params=params) as prh_response:
                if prh_response.status != 200:
                    # TODO: Add better error handling/logging here.
                    jobs[job_id]["status"] = "failed"
                    jobs[job_id]["results"] = {"error": "Failed to fetch data from PRH API"}
                    return
                prh_data = await prh_response.json()

            # TODO: Adjust parsing based on actual PRH API response structure.
            # Assume prh_data contains a list of companies under the key "results".
            company_list = prh_data.get("results", [])
            for company in company_list:
                # TODO: Replace the field names as per actual API response.
                # Here we're assuming a sample structure.
                is_active = company.get("status", "").lower() == "active"
                if not is_active:
                    continue

                # Retrieve minimal fields from the PRH API result.
                company_name_val = company.get("name", "Unknown")
                business_id_val = company.get("businessId", "Unknown")
                company_type_val = company.get("companyForm", "Unknown")
                registration_date_val = company.get("registrationDate", "Unknown")
                status_val = "Active" if is_active else "Inactive"
                lei_val = "Not Available"

                # Enrich data by fetching LEI
                lei_url = LEI_API_URL_TEMPLATE.format(businessId=business_id_val)
                try:
                    async with session.get(lei_url) as lei_response:
                        if lei_response.status == 200:
                            lei_data = await lei_response.json()
                            # TODO: Adjust the LEI data extraction based on the LEI API response.
                            lei_val = lei_data.get("lei", "Not Available")
                        else:
                            lei_val = "Not Available"
                except Exception as e:
                    # Log exception or handle accordingly.
                    lei_val = "Not Available"

                results.append({
                    "companyName": company_name_val,
                    "businessId": business_id_val,
                    "companyType": company_type_val,
                    "registrationDate": registration_date_val,
                    "status": status_val,
                    "lei": lei_val,
                })
            
            # If output_format is csv, we convert the results accordingly.
            if output_format == "csv":
                # TODO: Implement CSV conversion if required.
                # For now, we are returning JSON.
                pass

        jobs[job_id]["results"] = results
        jobs[job_id]["status"] = "completed"
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["results"] = {"error": str(e)}


# Mermaid sequence diagram representing user-app interaction.
MERMAID_DIAGRAM = """
sequenceDiagram
    participant U as User
    participant A as Application Server
    participant PRH as Finnish Companies API
    participant LEI as LEI Data Source

    U->>A: POST /companies/search { "companyName": "Example Corp", ... }
    A->>PRH: GET companies?name=Example Corp&page=1
    PRH-->>A: Return list of companies
    A->>A: Filter out inactive companies
    loop For each active company
      A->>LEI: GET LEI data for businessId
      LEI-->>A: Return LEI or Not Available
    end
    A-->>U: Return { "job_id": "...", "status": "processing" }
    U->>A: GET /companies/results/{job_id}
    A-->>U: Return stored search result data when ready
"""

@app.route("/mermaid")
async def mermaid():
    # Endpoint to view the Mermaid diagram if needed.
    return MERMAID_DIAGRAM, 200

if __name__ == '__main__':
    # Using threaded=True for development/testing purposes.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
------------------------------------------------

Notes:
• The PRH API response parsing and LEI API integration use placeholder field names and URLs.
• TODO markers indicate where more robust error handling, actual API response parsing, and a proper CSV conversion should be implemented.
• This prototype verifies the user experience while fulfilling the provided requirements.