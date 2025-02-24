#!/usr/bin/env python3
import asyncio
import uuid
import datetime
import json  # for parsing filters
from dataclasses import dataclass
from quart import Quart, request, jsonify, Response
from quart_schema import QuartSchema, validate_request, validate_response  # Workaround note: For POST, route decorator must be first, then validations.
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Request and response dataclasses for validation using only primitives.
@dataclass
class CompanySearchRequest:
    companyName: str
    filters: str = ""  # JSON string for filters (TODO: improve type handling)
    outputFormat: str = "json"

@dataclass
class CompanySearchResponse:
    resultId: str
    status: str

# In-memory cache for job persistence (mock persistence)
entity_jobs = {}

# Constants for external API endpoints
PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3"
# TODO: Replace with real external LEI data source URL when known.
LEI_API_URL = "https://example.com/lei"  # Placeholder URL

async def fetch_companies(session: aiohttp.ClientSession, company_name: str, filters: dict) -> dict:
    """
    Calls the Finnish Companies Registry API with the given company name and filters.
    """
    params = {"name": company_name}
    # TODO: Add additional parameters from filters if required.
    url = f"{PRH_API_BASE}/companies"
    async with session.get(url, params=params) as resp:
        if resp.status != 200:
            # TODO: Use proper error handling and logging.
            return {"companies": []}
        return await resp.json()

async def fetch_lei_for_company(session: aiohttp.ClientSession, company: dict) -> str:
    """
    Mocks external LEI lookup for a given company.
    In production, call the actual LEI API or a reliable source.
    """
    # TODO: Replace this mock with an actual API call to fetch LEI.
    await asyncio.sleep(0.2)
    if company.get("status", "").lower() == "active":
        return "MOCK_LEI_12345"
    return "Not Available"

async def process_entity(job_id: str, data: dict):
    """
    Processes the request by calling external APIs, filtering inactive companies,
    and enriching active companies with LEI data.
    Updates the in-memory cache with the final result.
    """
    async with aiohttp.ClientSession() as session:
        company_name = data.get("companyName")
        filters_str = data.get("filters", "")
        try:
            filters = json.loads(filters_str) if filters_str else {}
        except Exception:
            filters = {}
        companies_data = await fetch_companies(session, company_name, filters)
        companies = companies_data.get("companies", [])
        
        active_companies = []
        for comp in companies:
            if comp.get("status", "").lower() == "active":
                active_companies.append(comp)
                
        enriched_companies = []
        for comp in active_companies:
            lei = await fetch_lei_for_company(session, comp)
            enriched_company = {
                "companyName": comp.get("companyName", "Unknown"),
                "businessId": comp.get("businessId", "Unknown"),
                "companyType": comp.get("companyType", "Unknown"),
                "registrationDate": comp.get("registrationDate", "Unknown"),
                "status": "Active",
                "lei": lei
            }
            enriched_companies.append(enriched_company)
        
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = enriched_companies

# Workaround for quart-schema issue: For POST endpoints, the route decorator must be listed first.
@app.route("/companies/search", methods=["POST"])
@validate_request(CompanySearchRequest)  # For POST: put validate_request after @app.route
@validate_response(CompanySearchResponse, 202)
async def companies_search(data: CompanySearchRequest):
    """
    Endpoint to search for companies, filter inactive ones,
    enrich them with LEI, and store the result.
    """
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat() + "Z"
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}
    # Convert the dataclass to dict for processing.
    data_dict = data.__dict__
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, data_dict))
    return CompanySearchResponse(resultId=job_id, status="processing"), 202

@app.route("/companies/result/<job_id>", methods=["GET"])
async def companies_result(job_id):
    """
    Endpoint to retrieve results for a given job_id.
    """
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Result ID not found"}), 404
    if job["status"] != "completed":
        return jsonify({"resultId": job_id, "status": job["status"]}), 202
    output_format = request.args.get("outputFormat", "json").lower()
    if output_format == "csv":
        # TODO: Implement a proper CSV conversion if required.
        csv_data = "companyName,businessId,companyType,registrationDate,status,lei\n"
        for comp in job["result"]:
            csv_row = f'{comp["companyName"]},{comp["businessId"]},{comp["companyType"]},' \
                      f'{comp["registrationDate"]},{comp["status"]},{comp["lei"]}\n'
            csv_data += csv_row
        return Response(csv_data, mimetype="text/csv")
    return jsonify({"resultId": job_id, "status": job["status"], "companies": job["result"]})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)