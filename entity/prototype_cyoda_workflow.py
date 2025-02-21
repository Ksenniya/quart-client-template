Yes—it’s not only possible but also a good design decision to move as much asynchronous processing (or any business logic) as possible out of your endpoint controllers. By shifting that logic into the dedicated workflow function (process_{entity_name}), you “thin out” your controllers and make your code more robust and easier to test.

In our current implementation the POST endpoint immediately creates a job record and then separately fires off an asynchronous task (via asyncio.create_task) that enriches the data before updating the job record. Instead, we can shift that external API call and enrichment logic directly into the workflow function. That way, when add_item is invoked, the workflow function is automatically executed on the job data before it’s persisted.

Keep in mind that in the workflow function:
 • You can execute asynchronous code (like external API calls).
 • You can modify the entity directly, for example, adding a processed timestamp or enrichment data.
 • You are not allowed to perform any add/update/delete operations on the same entity via entity_service since the entity’s altered state is automatically persisted after the workflow execution.

Below is an example refactoring that moves the previously “fire and forget” asynchronous processing into the workflow function:

------------------------------------------------------------
#!/usr/bin/env python3
"""
Refactored prototype implementation for the Finnish Companies Data Retrieval and Enrichment Application.

Notes:
 • External API calls are performed with aiohttp.ClientSession.
 • Persistence is now implemented via an external entity_service.
 • The entity_service.add_item() function now takes a workflow function that will be applied asynchronously
   on the entity (job record) right before that entity is persisted. This decouples processing logic from the controller.
 • Decorators for request/response validation using quart-schema are applied.
"""

import asyncio
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
QuartSchema(app)

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
    # TODO: Add additional filters if needed

@dataclass
class CompanySearchResponse:
    searchId: str
    status: str

@dataclass
class PaginationQuery:
    page: int = 1
    pageSize: int = 100

# -----------------------------------------------------------------------------
# Workflow Function for Pre-persistence Processing
#
# This asynchronous workflow function is applied to the job entity before persisting.
# All asynchronous tasks (including external API calls for data retrieval and enrichment)
# can be moved here. This frees our endpoint controller from excessive logic.
#
# IMPORTANT:
# • Modify the entity state directly. Do not use entity_service functions to update the same entity.
# • If you need to fetch supplementary data for a different entity model, that is allowed.
# -----------------------------------------------------------------------------

async def process_companies_workflow(entity: dict):
    # In our example, we'll assume the search term is contained within the entity under "searchTerm".
    search_term = entity.get("searchTerm", "")
    async with aiohttp.ClientSession() as session:
        try:
            # Call external API to fetch Finnish Companies Data.
            base_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
            url = f"{base_url}?name={search_term}"
            async with session.get(url) as resp:
                # Adapt error handling if necessary.
                companies_data = await resp.json()
        except Exception as e:
            entity["status"] = "failed"
            entity["error"] = f"Error retrieving companies: {str(e)}"
            return entity

        # Process and enrich the company data.
        results = []
        for company in companies_data.get("results", []):
            if company.get("status", "").lower() != "active":
                continue

            business_id = company.get("businessId", "")
            lei_url = f"https://mock-lei-api.com/api/lei?businessId={business_id}"  # Replace with a real endpoint if needed

            try:
                async with session.get(lei_url) as lei_resp:
                    if lei_resp.status == 200:
                        lei_data = await lei_resp.json()
                        company["lei"] = lei_data.get("lei", "Not Available")
                    else:
                        company["lei"] = "Not Available"
            except Exception:
                company["lei"] = "Not Available"

            results.append({
                "companyName": company.get("companyName", "Unknown"),
                "businessId": business_id,
                "companyType": company.get("companyType", "Unknown"),
                "registrationDate": company.get("registrationDate", "Unknown"),
                "status": "Active",
                "lei": company.get("lei")
            })

        # Update the job entity state.
        entity["results"] = results
        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat()
        return entity

# -----------------------------------------------------------------------------
# POST Endpoint: Trigger data processing and enrichment.
#
# Instead of firing off a separate asynchronous background task,
# we embed the asynchronous processing logic in a workflow function
# that will be executed immediately (asynchronously) as part of the persistence chain.
# -----------------------------------------------------------------------------

@app.route('/companies/search', methods=['POST'])
@validate_request(CompanySearch)  # For POST endpoints, this comes after the route decorator.
@validate_response(CompanySearchResponse, 200)
async def search_companies(data: CompanySearch):
    # Prepare the job record with some initial data.
    requested_at = datetime.utcnow().isoformat()
    # We store the search term so the workflow function can use it to query external APIs.
    job_data = {
        "status": "processing",
        "requestedAt": requested_at,
        "results": [],
        "searchTerm": data.name  # Pass search parameter to workflow
    }
    # Use entity_service.add_item with the workflow function to process the entity.
    job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_data,
        workflow=process_companies_workflow  # Workflow function applied asynchronously before persistence.
    )
    # The entity_service.add_item call will execute the workflow (which performs the async processing)
    # and then persist the updated state of the job entity.
    return CompanySearchResponse(searchId=job_id, status="processing")

# -----------------------------------------------------------------------------
# GET Endpoint: Retrieve processed results.
# -----------------------------------------------------------------------------

@validate_querystring(PaginationQuery)
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

In this refactored design:

1. The controller (search_companies endpoint) is responsible only for assembling the minimal job record and invoking entity_service.add_item.
2. All the asynchronous processing logic—such as fetching and enriching company data via external APIs—is encapsulated in process_companies_workflow.
3. The workflow function modifies the entity directly. Once done, the updated state is persisted by the entity_service.

This approach leads to thinner, more focused controllers while keeping the processing logic centralized and robust.