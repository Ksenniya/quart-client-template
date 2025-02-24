#!/usr/bin/env python3
import asyncio
import uuid
import datetime
import json  # for parsing filters
from dataclasses import dataclass
from quart import Quart, request, jsonify, Response
from quart_schema import QuartSchema, validate_request, validate_response  # Workaround note: For POST, route decorator must be first, then validations.
import aiohttp

from common.config.config import ENTITY_VERSION  # Import constant
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

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
    Updates the job record via the external entity_service with the final result.
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
        
        # Update the job status to completed with result via external service
        update_data = {
            "technical_id": job_id,
            "status": "completed",
            "result": enriched_companies
        }
        entity_service.update_item(
            token=cyoda_token,
            entity_model="companies_job",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=update_data,
            meta={}
        )

# Workaround for quart-schema issue: For POST endpoints, the route decorator must be listed first.
@app.route("/companies/search", methods=["POST"])
@validate_request(CompanySearchRequest)  # For POST: put validate_request after @app.route
@validate_response(CompanySearchResponse, 202)
async def companies_search(data: CompanySearchRequest):
    """
    Endpoint to search for companies, filter inactive ones,
    enrich them with LEI, and store the result via the external entity_service.
    """
    requested_at = datetime.datetime.utcnow().isoformat() + "Z"
    # Prepare initial job data
    job_data = {
        "status": "processing",
        "requestedAt": requested_at,
        "companySearchData": data.__dict__
    }
    # Add job record via external service and get the generated id
    job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies_job",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_data  # the validated data object
    )
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, data.__dict__))
    return CompanySearchResponse(resultId=job_id, status="processing"), 202

@app.route("/companies/result/<job_id>", methods=["GET"])
async def companies_result(job_id):
    """
    Endpoint to retrieve results for a given job_id via external entity_service.
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
        # TODO: Implement a proper CSV conversion if required.
        csv_data = "companyName,businessId,companyType,registrationDate,status,lei\n"
        for comp in job.get("result", []):
            csv_row = f'{comp.get("companyName")},{comp.get("businessId")},{comp.get("companyType")},' \
                      f'{comp.get("registrationDate")},{comp.get("status")},{comp.get("lei")}\n'
            csv_data += csv_row
        return Response(csv_data, mimetype="text/csv")
    return jsonify({"resultId": job_id, "status": job.get("status"), "companies": job.get("result")})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)