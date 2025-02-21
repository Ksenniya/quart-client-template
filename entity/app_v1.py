#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete refactored prototype implementation for the Finnish Companies Data Retrieval
and Enrichment Application.

Design highlights:
   is applied asynchronously on the job entity (data structure) immediately before persistence.
   the workflow function (process_companies_workflow).
   accordingly. All exceptions are caught and saved on the entity.
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
QuartSchema(app)  # Integrate quart_schema into the Quart app

# -----------------------------------------------------------------------------
# Startup Initialization
# -----------------------------------------------------------------------------

@app.before_serving
async def startup():
    # Initialize connection or configuration for your external system.
    await init_cyoda(cyoda_token)

# -----------------------------------------------------------------------------
# Data Models for validation
# -----------------------------------------------------------------------------

@dataclass
class CompanySearch:
    name: str
    # Additional filters (location, companyForm, etc.) can be added here as primitives.

@dataclass
class CompanySearchResponse:
    searchId: str
    status: str

@dataclass
class PaginationQuery:
    page: int = 1
    pageSize: int = 100

# -----------------------------------------------------------------------------
# POST Endpoint: /companies/search
#
# Initiates a company search by creating a job entity and applying the workflow function.
# All the asynchronous processing is handled in the workflow function.
# -----------------------------------------------------------------------------

@app.route('/companies/search', methods=['POST'])
@validate_request(CompanySearch)  # Validates the POST request body
@validate_response(CompanySearchResponse, 200)
async def search_companies(data: CompanySearch):
    # Record the time at which the request was received.
    requested_at = datetime.utcnow().isoformat()
    # Construct the job record; the search term is stored for later use by the workflow.
    job_data = {
        "status": "processing",
        "requestedAt": requested_at,
        "results": [],
        "searchTerm": data.name  # Pass search term for later external API look-up.
    }
    # Call entity_service.add_item with the workflow function.
    # The workflow function will be invoked asynchronously before persisting the entity.
    try:
        job_id = entity_service.add_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,  # Always use this constant.
            entity=job_data,
            workflow=process_companies_workflow  # Apply asynchronous processing before persistence.
        )
    except Exception as e:
        # In case add_item itself raises an exception, return error response.
        return jsonify({"error": f"Failed to create job: {str(e)}"}), 500

    # Respond quickly with the job id; the workflow continues to run asynchronously in the background.
    return CompanySearchResponse(searchId=job_id, status="processing")

# -----------------------------------------------------------------------------
# GET Endpoint: /companies/result/<search_id>
#
# Retrieve the job entity with pagination for the results.
# -----------------------------------------------------------------------------

@validate_querystring(PaginationQuery)
@app.route('/companies/result/<string:search_id>', methods=['GET'])
async def get_companies_result(search_id: str):
    # Attempt to retrieve the job entity.
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=search_id
    )
    if not job:
        return jsonify({"error": "Job not found"}), 404

    # Validate pagination query parameters.
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("pageSize", 100))
        if page < 1 or page_size < 1:
            raise ValueError("Pagination parameters must be positive integers.")
    except ValueError as ve:
        return jsonify({"error": f"Invalid pagination parameters: {str(ve)}"}), 400

    results = job.get("results", [])
    total_results = len(results)
    # Compute total pages ensuring division by zero is prevented.
    total_pages = (total_results + page_size - 1) // page_size if page_size else 1
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
# Entry Point
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    # Running the app with threaded=True ensures compatibility with asynchronous execution.
    # use_reloader=False avoids spawning multiple instances.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
