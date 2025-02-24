#!/usr/bin/env python3
import asyncio
import uuid
import datetime
import json  # for parsing filters
from dataclasses import dataclass
from quart import Quart, request, jsonify, Response
from quart_schema import QuartSchema, validate_request, validate_response  # For POST, route decorator must be first, then validations.
import aiohttp

from common.config.config import ENTITY_VERSION  # Import constant
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Request and response dataclasses for input/output validation.
@dataclass
class CompanySearchRequest:
    companyName: str
    filters: str = ""  # JSON string for filters (could be improved)
    outputFormat: str = "json"

@dataclass
class CompanySearchResponse:
    resultId: str
    status: str

# Constants for external API endpoints.
PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3"
LEI_API_URL = "https://example.com/lei"  # Placeholder URL

async def fetch_companies(session: aiohttp.ClientSession, company_name: str, filters: dict) -> dict:
    """
    Calls the Finnish Companies Registry API with the given company name and filters.
    """
    params = {"name": company_name}
    # Additional parameters from filters can be appended here.
    url = f"{PRH_API_BASE}/companies"
    async with session.get(url, params=params) as resp:
        if resp.status != 200:
            # Log error or handle failure appropriately.
            return {"companies": []}
        return await resp.json()

async def fetch_lei_for_company(session: aiohttp.ClientSession, company: dict) -> str:
    """
    Mocks an external LEI lookup for a given company.
    In production, this should call the actual LEI API.
    """
    await asyncio.sleep(0.2)
    if company.get("status", "").lower() == "active":
        return "MOCK_LEI_12345"
    return "Not Available"

async def process_companies_job(entity: dict):
    """
    Workflow function applied to companies_job entity before persistence.
    This function is invoked asynchronously by entity_service.add_item.
    It enriches the search results by calling external APIs and updates the entity state.
    """
    # Retrieve the search data from the entity.
    data = entity.get("companySearchData", {})
    async with aiohttp.ClientSession() as session:
        company_name = data.get("companyName")
        filters_str = data.get("filters", "")
        try:
            filters = json.loads(filters_str) if filters_str else {}
        except Exception:
            filters = {}
        companies_data = await fetch_companies(session, company_name, filters)
        companies = companies_data.get("companies", [])
        
        # Filter out only active companies.
        active_companies = [comp for comp in companies if comp.get("status", "").lower() == "active"]
        
        # Enrich active companies with LEI data.
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
    
    # Directly modify the entity state; the updated state will be persisted.
    entity["status"] = "completed"
    entity["result"] = enriched_companies
    # Return the modified entity if needed.
    return entity

# Endpoint to trigger company search.
# The endpoint is now very lean; it only prepares the job data and delegates processing to the workflow.
@app.route("/companies/search", methods=["POST"])
@validate_request(CompanySearchRequest)  # Validate input data.
@validate_response(CompanySearchResponse, 202)
async def companies_search(data: CompanySearchRequest):
    """
    Endpoint to search for companies.
    The heavy lifting (API calls, enrichment, filtering) is handled inside the workflow function.
    """
    requested_at = datetime.datetime.utcnow().isoformat() + "Z"
    job_data = {
        "status": "processing",
        "requestedAt": requested_at,
        "companySearchData": data.__dict__
    }
    # Create a new job with the attached workflow. The workflow function will be
    # executed asynchronously before the entity is persisted.
    job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies_job",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_data,  # the validated job data
        workflow=process_companies_job  # Workflow function handles asynchronous enrichment.
    )
    return CompanySearchResponse(resultId=job_id, status="processing"), 202

@app.route("/companies/result/<job_id>", methods=["GET"])
async def companies_result(job_id):
    """
    Endpoint to retrieve job results from entity_service.
    """
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies_job",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        return jsonify({"error": "Result ID not found"}), 404
    if job.get("status") != "completed":
        return jsonify({"resultId": job_id, "status": job.get("status")}), 202
    output_format = request.args.get("outputFormat", "json").lower()
    if output_format == "csv":
        # Convert the result to CSV format.
        csv_data = "companyName,businessId,companyType,registrationDate,status,lei\n"
        for comp in job.get("result", []):
            csv_row = f'{comp.get("companyName")},{comp.get("businessId")},{comp.get("companyType")},' \
                      f'{comp.get("registrationDate")},{comp.get("status")},{comp.get("lei")}\n'
            csv_data += csv_row
        return Response(csv_data, mimetype="text/csv")
    return jsonify({"resultId": job_id, "status": job.get("status"), "companies": job.get("result")})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)