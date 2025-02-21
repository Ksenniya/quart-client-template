Below is one complete refactored application that follows these principles. All asynchronous business logic is now encapsulated in dedicated workflow functions (in this case, process_job) so that the controller (HTTP endpoints) is kept lean. In this solution:

• The POST /companies/search endpoint creates a job record and passes process_job as the workflow argument. The entity_service implementation is expected to invoke the workflow (asynchronously) on the record before/or right after the entity is persisted.  
• The process_job function does all the heavy lifting (external API calls, filtering, enrichment) in an async-safe manner with proper exception handling.  
• Any potential issues (e.g. failed network calls or JSON decoding errors) are caught, and the job record is updated accordingly.  
• There is careful use of aiohttp’s async ClientSession as well as error handling so that even if a single external call fails, the job is marked failed and not left in an inconsistent state.

Below is the complete code:

------------------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
import json

from dataclasses import dataclass
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response
import aiohttp

# External dependencies and shared constants; these must be correctly implemented
# elsewhere in the project.
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # initialize QuartSchema

# Constants for external API endpoints.
PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
# TODO: Replace LEI_API_URL_TEMPLATE with a valid endpoint for LEI lookup.
LEI_API_URL_TEMPLATE = "https://api.example.com/lei?businessId={businessId}"

# Startup logic to initialize cyoda.
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

# ---------------------------------------------------------------------------
# Endpoints (Controllers)
# ---------------------------------------------------------------------------
# POST /companies/search
# This endpoint is now responsible only for:
# • Validating the request.
# • Generating a job record.
# • Persisting the job record using the external entity_service.add_item.
# The workflow function process_job is registered via the workflow parameter.
@app.route("/companies/search", methods=["POST"])
@validate_request(SearchRequest)  # should be second for POST requests
@validate_response(SearchResponse, 202)
async def search_companies(data: SearchRequest):
    company_name = data.companyName.strip()
    if not company_name:
        return jsonify({"error": "Missing required field 'companyName'"}), 400

    page = data.page
    output_format = data.outputFormat.lower()

    # Generate a unique job id.
    job_id = str(uuid.uuid4())
    # Create the job record to be processed.
    job_data = {
        "job_id": job_id,
        "status": "processing",
        "requestedAt": datetime.datetime.utcnow().isoformat(),
        "results": None,
        "companyName": company_name,
        "page": page,
        "outputFormat": output_format,
    }

    # Persist job_data via external entity_service.
    # Pass the workflow function (process_job) that will do all the asynchronous work.
    new_job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="job",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_data,  # data record including additional metadata
        workflow=process_job  # workflow function invoked asynchronously to process this job.
    )
    # new_job_id is expected to be the job identifier.

    # The endpoint returns immediately with the job id, while process_job works in background.
    return SearchResponse(job_id=new_job_id, status="processing"), 202

# GET /companies/results/<job_id>
@app.route("/companies/results/<job_id>", methods=["GET"])
async def get_results(job_id):
    # Obtain the job record using the external entity_service.
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="job",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if job is None:
        abort(404, description="Job ID not found")

    # If still processing, let the client know the request is not yet complete.
    if job.get("status", "").lower() == "processing":
        return jsonify({"job_id": job_id, "status": "processing"}), 202

    if job.get("results") is None:
        return jsonify({"error": "No results available"}), 500

    # Return the completed job data. Note: You may refine this output as needed.
    return jsonify({
        "job_id": job_id,
        "status": "completed",
        "results": job.get("results"),
    }), 200

# ---------------------------------------------------------------------------
# Workflow Functions (Business Logic Handlers)
# ---------------------------------------------------------------------------
# process_job is a workflow function that will be invoked by entity_service right
# before (or immediately after) persisting the entity in storage.
# This function performs all asynchronous operations such as interacting with external APIs.
#
# It is critical to handle exceptions so that any errors are captured and the job
# record is updated with a proper error message.
async def process_job(job):
    job_id = job.get("job_id")
    company_name = job.get("companyName")
    page = job.get("page")
    output_format = job.get("outputFormat")
    results = []

    try:
        # Use a single ClientSession to make external HTTP calls.
        async with aiohttp.ClientSession() as session:
            # Build the parameters to query the PRH API for company data.
            params = {
                "name": company_name,
                "page": page
            }
            async with session.get(PRH_API_BASE, params=params) as prh_response:
                if prh_response.status != 200:
                    # Log failure details and update the job as failed.
                    failed_record = {
                        "job_id": job_id,
                        "status": "failed",
                        "results": {"error": "Failed to fetch data from PRH API (HTTP status %s)" % prh_response.status}
                    }
                    entity_service.update_item(
                        token=cyoda_token,
                        entity_model="job",
                        entity_version=ENTITY_VERSION,
                        entity=failed_record,
                        meta={}
                    )
                    return  # Exit the workflow function.
                try:
                    prh_data = await prh_response.json()
                except Exception as json_err:
                    failed_record = {
                        "job_id": job_id,
                        "status": "failed",
                        "results": {"error": "Failed to decode JSON from PRH API: %s" % str(json_err)}
                    }
                    entity_service.update_item(
                        token=cyoda_token,
                        entity_model="job",
                        entity_version=ENTITY_VERSION,
                        entity=failed_record,
                        meta={}
                    )
                    return

            # Assume the PRH data contains company listings in the key "results".
            company_list = prh_data.get("results", [])
            # Process each company record.
            for company in company_list:
                # Ensure that we process only "active" companies.
                is_active = company.get("status", "").lower() == "active"
                if not is_active:
                    continue

                company_name_val = company.get("name", "Unknown")
                business_id_val = company.get("businessId", "Unknown")
                company_type_val = company.get("companyForm", "Unknown")
                registration_date_val = company.get("registrationDate", "Unknown")
                lei_val = "Not Available"  # Default value if enrichment fails.

                # Enrich the company data by fetching LEI data.
                lei_url = LEI_API_URL_TEMPLATE.format(businessId=business_id_val)
                try:
                    async with session.get(lei_url) as lei_response:
                        if lei_response.status == 200:
                            try:
                                lei_data = await lei_response.json()
                                lei_val = lei_data.get("lei", "Not Available")
                            except Exception as lei_json_err:
                                lei_val = "Not Available"
                        else:
                            lei_val = "Not Available"
                except Exception as e:
                    lei_val = "Not Available"

                results.append({
                    "companyName": company_name_val,
                    "businessId": business_id_val,
                    "companyType": company_type_val,
                    "registrationDate": registration_date_val,
                    "status": "Active",
                    "lei": lei_val,
                })

            # If the requested output format is CSV, then convert the results into CSV.
            # The conversion here is simplistic. For production you might use libraries such as csv.
            if output_format == "csv":
                try:
                    # Convert list of dictionaries to CSV string.
                    import io, csv
                    output = io.StringIO()
                    if results:
                        headers = results[0].keys()
                        writer = csv.DictWriter(output, fieldnames=headers)
                        writer.writeheader()
                        writer.writerows(results)
                    # Store CSV string instead of JSON data.
                    results = output.getvalue()
                except Exception as csv_err:
                    # If CSV conversion fails, update the job as failed.
                    failed_record = {
                        "job_id": job_id,
                        "status": "failed",
                        "results": {"error": "CSV conversion failed: %s" % str(csv_err)}
                    }
                    entity_service.update_item(
                        token=cyoda_token,
                        entity_model="job",
                        entity_version=ENTITY_VERSION,
                        entity=failed_record,
                        meta={}
                    )
                    return

        # Once processing is finished, update the job record as "completed".
        updated_job = {
            "job_id": job_id,
            "status": "completed",
            "results": results
        }
        entity_service.update_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            entity=updated_job,
            meta={}
        )
    except Exception as e:
        # Catch-all for any unexpected errors.
        error_update = {
            "job_id": job_id,
            "status": "failed",
            "results": {"error": "Unexpected error occurred: %s" % str(e)}
        }
        try:
            entity_service.update_item(
                token=cyoda_token,
                entity_model="job",
                entity_version=ENTITY_VERSION,
                entity=error_update,
                meta={}
            )
        except Exception as update_err:
            # Log error in updating job record if needed.
            pass

# ---------------------------------------------------------------------------
# Additional Endpoints
# ---------------------------------------------------------------------------
# Serving a Mermaid diagram that visually explains the flow.
@app.route("/mermaid")
async def mermaid():
    MERMAID_DIAGRAM = """
    sequenceDiagram
        participant U as User
        participant A as Application Server
        participant PRH as Finnish Companies API
        participant LEI as LEI Data Source

        U->>A: POST /companies/search { "companyName": "Example Corp", ... }
        A->>EntityService: add_item(entity=job_data, workflow=process_job)
        EntityService->>A: job_id returned
        A-->>U: Return { "job_id": "...", "status": "processing" }
        Note over EntityService: process_job is invoked asynchronously
        process_job->>PRH: GET companies?name=Example Corp&page=1
        PRH-->>process_job: List of companies
        process_job->>process_job: Filter inactive companies and enrich with LEI
        process_job->>EntityService: update_item(job=completed job record)
        U->>A: GET /companies/results/{job_id}
        A-->>U: Return completed job record if available
    """
    return MERMAID_DIAGRAM, 200

# ---------------------------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    # Using threaded=True for development/testing purposes.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

------------------------------------------------------------

Important considerations addressed in this implementation:
1. All business logic (external HTTP calls, filtering active companies, and CSV conversion) is moved into the process_job workflow function. This keeps the controller logic simple.
2. The aiohttp.ClientSession is used effectively (with async with) so that resources are properly cleaned up.
3. Every external call is wrapped in try/except blocks. In case of failure (or JSON decoding errors), the job record is updated accordingly to avoid hanging or inconsistent states.
4. The CSV conversion is done only if requested. Should it fail, the failure is recorded.
5. Updates to the job are performed via entity_service.update_item. Make sure that the entity_service implementation prevents infinite recursion (as no job record should invoke further job-processing).
6. The workflow function is asynchronous, ensuring that the heavy lifting does not block HTTP responses.

This refactored design makes the application more robust and keeps the endpoint code focused on HTTP-related concerns while delegating all long-running logic to the asynchronous workflow function.