Below is one acceptable complete solution. In this version the call to entity_service.add_item now supplies a workflow function (process_job) that will be applied asynchronously to the job record before (or immediately after) it is persisted. The workflow function is implemented as an async function that receives the created entity as its only argument, extracts the needed values, calls the external APIs, and finally updates the job record via entity_service.update_item. (Note that since the workflow function works on an entity of model "job", it must not perform add/update/delete on another "job" entity to avoid recursion.)

Here is the full refactored code:

------------------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
import json

from dataclasses import dataclass
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring
import aiohttp

# Replace references to our external entity service and other shared constants.
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # initialize QuartSchema

# Constants for external API endpoints
PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
# TODO: Replace LEI_API_URL_TEMPLATE with a valid endpoint for LEI lookup.
LEI_API_URL_TEMPLATE = "https://api.example.com/lei?businessId={businessId}"

# Startup code to initialize cyoda.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

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

# POST /companies/search
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

    # Create an initial job record.
    # We generate a job id so that subsequent updates include it,
    # but we pass the whole record to the entity_service.
    job_id = str(uuid.uuid4())
    job_data = {
        "job_id": job_id,
        "status": "processing",
        "requestedAt": datetime.datetime.utcnow().isoformat(),
        "results": None,
        "companyName": company_name,
        "page": page,
        "outputFormat": output_format,
    }

    # Save initial job record using the external entity_service.
    # Note the additional parameter "workflow" that points to process_job.
    new_job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="job",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_data,  # the validated data object with extra metadata
        workflow=process_job  # Workflow function applied asynchronously to the job entity.
    )
    # (new_job_id here is expected to be the identifier for this job.)

    # No need to schedule async processing manually.
    return SearchResponse(job_id=new_job_id, status="processing"), 202

# GET /companies/results/<job_id>
@app.route("/companies/results/<job_id>", methods=["GET"])
async def get_results(job_id):
    # Retrieve stored job from external entity_service.
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="job",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if job is None:
        abort(404, description="Job ID not found")

    if job.get("status") == "processing":
        return jsonify({"job_id": job_id, "status": "processing"}), 202

    if job.get("results") is None:
        return jsonify({"error": "No results available"}), 500

    # For this prototype, we return JSON regardless of the requested output format.
    return jsonify({
        "job_id": job_id,
        "status": "completed",
        "results": job.get("results"),
    }), 200

# Workflow function for job entities.
# This function gets applied asynchronously to the job record.
async def process_job(job):
    # Extract values from the job entity.
    job_id = job.get("job_id")
    company_name = job.get("companyName")
    page = job.get("page")
    output_format = job.get("outputFormat")
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
                    # Update job as failed using entity_service.
                    failed_record = {
                        "job_id": job_id,
                        "status": "failed",
                        "results": {"error": "Failed to fetch data from PRH API"}
                    }
                    entity_service.update_item(
                        token=cyoda_token,
                        entity_model="job",
                        entity_version=ENTITY_VERSION,  # always use this constant
                        entity=failed_record,
                        meta={}
                    )
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

        # Update job as completed.
        updated_job = {
            "job_id": job_id,
            "status": "completed",
            "results": results
        }
        entity_service.update_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=updated_job,
            meta={}
        )
    except Exception as e:
        # Update job as failed.
        error_update = {
            "job_id": job_id,
            "status": "failed",
            "results": {"error": str(e)}
        }
        entity_service.update_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=error_update,
            meta={}
        )

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

------------------------------------------------------------

Notes:
1. In /companies/search the initial job record is saved externally via entity_service.add_item with the new workflow parameter process_job.
2. The workflow function process_job receives the job entity as its only argument and asynchronously performs the external API calls, filters and enriches the company data, and finally updates the job record using entity_service.update_item.
3. The GET /companies/results/<job_id> endpoint retrieves the job and returns current status/results.
4. All business logic (making external API calls, filtering, and enriching with LEI) remains essentially unchanged.
5. Remember to adjust the TODO sections based on your actual API responses and CSV formatting needs.

This refactoring meets the requirement to add a workflow function parameter to entity_service.add_item while keeping the overall functionality intact.