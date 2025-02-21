#!/usr/bin/env python3
import asyncio
import uuid
import datetime
import json

from dataclasses import dataclass
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # initialize QuartSchema

# In-memory store for job results; in production, replace with a persistent store.
jobs = {}

# Constants for external API endpoints
PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
# TODO: Replace LEI_API_URL_TEMPLATE with a valid endpoint for LEI lookup.
LEI_API_URL_TEMPLATE = "https://api.example.com/lei?businessId={businessId}"

# Data models using only primitives.
@dataclass
class SearchRequest:
    companyName: str
    page: int = 1
    outputFormat: str = "json"

@dataclass
class SearchResponse:
    job_id: str
    status: str

# Note: For POST requests, the decorators must be applied in the order: 
# 1) @app.route, 2) @validate_request, 3) @validate_response.
# This is a workaround for an issue in quart-schema where ordering matters.

@app.route("/companies/search", methods=["POST"])
@validate_request(SearchRequest)  # should be second for POST requests
@validate_response(SearchResponse, 202)
async def search_companies(data: SearchRequest):
    # Data validated by quart-schema.
    company_name = data.companyName.strip()
    if not company_name:
        return jsonify({"error": "Missing required field 'companyName'"}), 400

    page = data.page
    output_format = data.outputFormat.lower()
    # Generate a unique job ID and store an initial record.
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.datetime.utcnow().isoformat(),
        "results": None,
    }

    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, company_name, page, output_format))

    return SearchResponse(job_id=job_id, status="processing"), 202

# For GET endpoints without a request body, validation of query strings is applied first.
# Since our GET /companies/results does not require query parameters from the body,
# we use standard parameter extraction.
@app.route("/companies/results/<job_id>", methods=["GET"])
async def get_results(job_id):
    job = jobs.get(job_id)
    if job is None:
        abort(404, description="Job ID not found")

    if job["status"] == "processing":
        return jsonify({"job_id": job_id, "status": "processing"}), 202

    if job["results"] is None:
        return jsonify({"error": "No results available"}), 500

    # For this prototype, we return JSON regardless of the requested output format.
    return jsonify({
        "job_id": job_id,
        "status": "completed",
        "results": job["results"],
    }), 200

async def process_entity(job_id, company_name, page, output_format):
    results = []
    try:
        async with aiohttp.ClientSession() as session:
            # Build query parameters for the PRH API.
            params = {
                "name": company_name,
                "page": page
            }
            async with session.get(PRH_API_BASE, params=params) as prh_response:
                if prh_response.status != 200:
                    # TODO: Add robust error handling/logging.
                    jobs[job_id]["status"] = "failed"
                    jobs[job_id]["results"] = {"error": "Failed to fetch data from PRH API"}
                    return
                prh_data = await prh_response.json()

            # TODO: Adjust parsing based on the actual PRH API response structure.
            # Here we assume prh_data contains a list of companies under the key "results".
            company_list = prh_data.get("results", [])
            for company in company_list:
                # TODO: Update field names as per the actual API response.
                is_active = company.get("status", "").lower() == "active"
                if not is_active:
                    continue

                company_name_val = company.get("name", "Unknown")
                business_id_val = company.get("businessId", "Unknown")
                company_type_val = company.get("companyForm", "Unknown")
                registration_date_val = company.get("registrationDate", "Unknown")
                # Mark status as Active (already filtered above) and prepare LEI.
                lei_val = "Not Available"

                # Enrich data by fetching LEI.
                lei_url = LEI_API_URL_TEMPLATE.format(businessId=business_id_val)
                try:
                    async with session.get(lei_url) as lei_response:
                        if lei_response.status == 200:
                            lei_data = await lei_response.json()
                            # TODO: Adjust LEI extraction based on the actual LEI API response.
                            lei_val = lei_data.get("lei", "Not Available")
                        else:
                            lei_val = "Not Available"
                except Exception as e:
                    # TODO: Log exception as needed.
                    lei_val = "Not Available"

                results.append({
                    "companyName": company_name_val,
                    "businessId": business_id_val,
                    "companyType": company_type_val,
                    "registrationDate": registration_date_val,
                    "status": "Active",
                    "lei": lei_val,
                })

            # If output_format is csv, we should convert the results accordingly.
            if output_format == "csv":
                # TODO: Implement CSV conversion if required.
                pass

        jobs[job_id]["results"] = results
        jobs[job_id]["status"] = "completed"
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["results"] = {"error": str(e)}

# Endpoint to view a Mermaid diagram illustrating the user-app interaction.
@app.route("/mermaid")
async def mermaid():
    # No validation needed.
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
          LEI-->>A: Return LEI or "Not Available"
        end
        A-->>U: Return { "job_id": "...", "status": "processing" }
        U->>A: GET /companies/results/{job_id}
        A-->>U: Return stored search result data when ready
    """
    return MERMAID_DIAGRAM, 200

if __name__ == '__main__':
    # Using threaded=True for development/testing purposes.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

# End of prototype.py
# This prototype uses aiohttp for external HTTP calls, Quart for routing, and a simple in-memory store for persistence.
# All external data retrieval and processing is executed via POST endpoints.
# TODOs indicate where additional implementation details (error handling, CSV conversion, actual API fields) are needed.
# The validate_request and validate_response decorators for POST routes and proper ordering on GET routes
# are implemented as a workaround for limitations in quart-schema.
