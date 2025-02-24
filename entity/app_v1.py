#!/usr/bin/env python3
import asyncio
import datetime
import json  # for parsing filters
from dataclasses import dataclass
from quart import Quart, request, jsonify, Response
from quart_schema import QuartSchema, validate_request, validate_response  # For POST: route decorator must be first, then validations.
import aiohttp

from common.config.config import ENTITY_VERSION  # Import constant
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

@app.before_serving
async def startup():
    try:
        await init_cyoda(cyoda_token)
    except Exception as e:
        # Log startup failure if needed.
        print("Failed to initialize cyoda:", e)
        raise e

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
LEI_API_URL = "https://example.com/lei"  # Placeholder URL for LEI lookup

# Endpoint to trigger company search.
# The endpoint is lean; it simply creates the job and defers processing to the workflow.
@app.route("/companies/search", methods=["POST"])
@validate_request(CompanySearchRequest)  # Validate input data.
@validate_response(CompanySearchResponse, 202)
async def companies_search(data: CompanySearchRequest):
    """
    Endpoint to search for companies.
    It creates a job record with initial state and attaches a workflow function
    that performs all heavy tasks (filtering, enrichment, etc.) asynchronously.
    """
    requested_at = datetime.datetime.utcnow().isoformat() + "Z"
    job_data = {
        "status": "processing",
        "requestedAt": requested_at,
        "companySearchData": data.__dict__
    }
    # Create a new job with the attached workflow.
    # The workflow function will be executed asynchronously before the entity is persisted.
    try:
        job_id = entity_service.add_item(
            token=cyoda_token,
            entity_model="companies_job",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=job_data,  # initial job data
            )
    except Exception as e:
        # Log error and return appropriate response.
        print("Error adding job item:", e)
        return jsonify({"error": "Failed to create job"}), 500

    return CompanySearchResponse(resultId=job_id, status="processing"), 202

# Endpoint to retrieve company search results.
@app.route("/companies/result/<job_id>", methods=["GET"])
async def companies_result(job_id):
    """
    Endpoint to retrieve the result for a given job_id.
    Returns job details in JSON or CSV format based on outputFormat query param.
    """
    try:
        job = entity_service.get_item(
            token=cyoda_token,
            entity_model="companies_job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
    except Exception as e:
        print("Error retrieving job:", e)
        return jsonify({"error": "Failed to retrieve job"}), 500

    if not job:
        return jsonify({"error": "Result ID not found"}), 404
    if job.get("status") != "completed":
        return jsonify({"resultId": job_id, "status": job.get("status")}), 202

    output_format = request.args.get("outputFormat", "json").lower()
    if output_format == "csv":
        # Convert result list to CSV format.
        csv_lines = ["companyName,businessId,companyType,registrationDate,status,lei"]
        for comp in job.get("result", []):
            # Ensure that missing fields are handled gracefully.
            csv_line = (
                f'{comp.get("companyName", "Unknown")},'
                f'{comp.get("businessId", "Unknown")},'
                f'{comp.get("companyType", "Unknown")},'
                f'{comp.get("registrationDate", "Unknown")},'
                f'{comp.get("status", "Unknown")},'
                f'{comp.get("lei", "Unknown")}'
            )
            csv_lines.append(csv_line)
        csv_data = "\n".join(csv_lines)
        return Response(csv_data, mimetype="text/csv")
    return jsonify({
        "resultId": job_id,
        "status": job.get("status"),
        "companies": job.get("result")
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)