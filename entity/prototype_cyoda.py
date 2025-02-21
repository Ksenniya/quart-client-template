Below is one acceptable refactoring of the file. In the code below all lookups, inserts, and updates formerly done against the in‑memory cache (the entity_jobs dictionary) have been replaced with calls to the external entity_service. (Note that if the provided entity_service functions are not sufficient to cover every in‑memory interaction, we “skip” that functionality and leave it as is.) Also note that the “companies” model is now used as the entity_model value. Finally, the startup code is added at the top as requested.

------------------------------------------------------------
#!/usr/bin/env python3
"""
Prototype implementation for the Finnish Companies Data Retrieval and Enrichment Application.

Notes:
 • External API calls are performed with aiohttp.ClientSession.
 • Persistence is now implemented via an external entity_service.
 • Decorators for request/response validation using quart-schema are applied.
   WORKAROUND: Due to an issue in quart-schema, for GET endpoints the validation decorator (@validate_querystring)
   is placed first and the endpoint function does not accept the validated model as an argument.
   For POST endpoints, the order is: route, then @validate_request, then @validate_response.
 • TODO comments denote areas where further clarification or real implementations are required.
"""

import asyncio
import uuid
from datetime import datetime
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring
import aiohttp

# External configuration and services
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)  # one‑line integration of QuartSchema

# Startup initialization for external system connection
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# -----------------------------------------------------------------------------
# Data models for validation
# -----------------------------------------------------------------------------

@dataclass
class CompanySearch:
    name: str
    # TODO: Add additional filters (e.g., location, companyForm) if needed, using only primitives

@dataclass
class CompanySearchResponse:
    searchId: str
    status: str

@dataclass
class PaginationQuery:
    page: int = 1
    pageSize: int = 100

# -----------------------------------------------------------------------------
# Asynchronous processing task.
#
# Note: This background task uses the entity_service functions to retrieve and update
# the job record rather than using an in‑memory cache.
# -----------------------------------------------------------------------------

async def process_entity(job_id: str, request_data: dict):
    # Retrieve current job record from the external service.
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    async with aiohttp.ClientSession() as session:
        try:
            # Build URL for the Finnish Companies Registry API using the provided company name.
            base_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
            name = request_data.get("name", "")
            # TODO: Expand URL building if additional filters are provided in request_data.
            url = f"{base_url}?name={name}"
            async with session.get(url) as resp:
                # TODO: Adapt error handling if external API returns non‑200 codes.
                companies_data = await resp.json()
        except Exception as e:
            job["status"] = "failed"
            job["error"] = f"Error retrieving companies: {str(e)}"
            entity_service.update_item(
                token=cyoda_token,
                entity_model="companies",
                entity_version=ENTITY_VERSION,
                entity=job,
                meta={}
            )
            return

        # Prepare list to store enriched company data.
        results = []
        # TODO: Adjust key names based on the actual API response schema.
        for company in companies_data.get("results", []):
            # Filter: Only consider companies marked as active.
            # TODO: Adjust condition based on the actual field defining active/inactive status.
            if company.get("status", "").lower() != "active":
                continue

            business_id = company.get("businessId", "")
            # Placeholder URL for LEI data enrichment.
            lei_url = f"https://mock-lei-api.com/api/lei?businessId={business_id}"  # TODO: Replace with a real LEI API endpoint

            try:
                async with session.get(lei_url) as lei_resp:
                    if lei_resp.status == 200:
                        lei_data = await lei_resp.json()
                        # TODO: Adjust based on actual response structure from the LEI API.
                        company["lei"] = lei_data.get("lei", "Not Available")
                    else:
                        company["lei"] = "Not Available"
            except Exception:
                company["lei"] = "Not Available"  # In case of errors, mark LEI as not available

            results.append({
                "companyName": company.get("companyName", "Unknown"),
                "businessId": business_id,
                "companyType": company.get("companyType", "Unknown"),
                "registrationDate": company.get("registrationDate", "Unknown"),
                "status": "Active",
                "lei": company.get("lei")
            })

        # Update the job record and save the processing result via the external service.
        job["results"] = results
        job["status"] = "completed"
        job["completedAt"] = datetime.utcnow().isoformat()
        entity_service.update_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            entity=job,
            meta={}
        )

# -----------------------------------------------------------------------------
# POST Endpoint: Trigger data processing and enrichment.
# -----------------------------------------------------------------------------

@app.route('/companies/search', methods=['POST'])
@validate_request(CompanySearch)          # For POST endpoints, validation comes after route decorator.
@validate_response(CompanySearchResponse, 200)
async def search_companies(data: CompanySearch):
    # Create a job record for this search.
    requested_at = datetime.utcnow().isoformat()
    job_data = {"status": "processing", "requestedAt": requested_at, "results": []}
    # Instead of a local job_id, we now call the external service.
    job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_data  # the validated job dictionary
    )
    # Fire-and-forget background processing task.
    # Pass the external job_id so that the process_entity function can lookup and update the record.
    asyncio.create_task(process_entity(job_id, {"name": data.name}))
    # Return the job id in the response so that the user can query data by id.
    return CompanySearchResponse(searchId=job_id, status="processing")

# -----------------------------------------------------------------------------
# GET Endpoint: Retrieve processed results.
# -----------------------------------------------------------------------------

@validate_querystring(PaginationQuery)  # WORKAROUND: Must be placed first for GET requests (do not pass as function argument).
@app.route('/companies/result/<string:search_id>', methods=['GET'])
async def get_companies_result(search_id: str):
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=search_id
    )
    if not job:
        return jsonify({"error": "Job not found"}), 404

    # Use standard approach to access query parameters - validated via decorator.
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("pageSize", 100))
    except ValueError:
        return jsonify({"error": "Invalid pagination parameters"}), 400

    results = job.get("results", [])
    total_results = len(results)
    total_pages = (total_results + page_size - 1) // page_size
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    paginated_results = results[start_index:end_index]

    response = {
        "searchId": search_id,
        "results": paginated_results,
        "pagination": {
            "currentPage": page,
            "pageSize": page_size,
            "totalPages": total_pages,
            "totalResults": total_results
        },
        "status": job.get("status")
    }
    return jsonify(response)

# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

------------------------------------------------------------

In this refactored version:
1. All local cache interactions (creation, retrieval, update) use the provided entity_service functions.
2. The JOB creation in POST is now performed with add_item (with the returned id added to the response).
3. The background process (process_entity) fetches and updates the job record externally.
4. The GET endpoint now calls entity_service.get_item() to retrieve the job record.

This solution preserves all essential business logic—data ingestion, external API calls, background processing, pagination—and mirrors the previous endpoint routes.