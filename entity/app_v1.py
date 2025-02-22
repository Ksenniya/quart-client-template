#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import uuid
import datetime
from dataclasses import dataclass

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response

# Import external service functions and constants
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Initialize quart-schema

# Startup hook to initialize cyoda
@app.before_serving
async def startup():
    try:
        await init_cyoda(cyoda_token)
    except Exception as e:
        # Log or handle startup issues appropriately.
        print(f"Error during startup initialization: {e}")
        raise

# Dataclasses for request/response validation
@dataclass
class CompanySearchRequest:
    companyName: str
    # Optionally, add additional filter fields if needed. Using a dict here for extensibility.
    filters: dict = None

@dataclass
class SearchResponse:
    searchId: str
    status: str
    message: str

# External endpoints (the local in‑memory cache is now replaced by external service calls)
PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3"
LEI_API_URL = "https://mock-lei-service.example.com/getLei"  # TODO: Replace with an official endpoint as needed

# POST endpoint: This controller is now very lightweight.
@app.route("/companies/search", methods=["POST"])
@validate_request(CompanySearchRequest)  # This decorator validates the incoming JSON payload.
@validate_response(SearchResponse, 200)
async def search_companies(data: CompanySearchRequest):
    """
    Endpoint to trigger the company search and enrichment process.

    This endpoint simply:
    """
    payload = data.__dict__
    current_time = datetime.datetime.utcnow().isoformat()

    # Generate a unique search id.
    search_id = str(uuid.uuid4())

    # Build the job entity record which includes the search input parameters.
    job_record = {
        "searchId": search_id,
        "status": "processing",
        "requestedAt": current_time,
        "results": None,
        # Save search criteria. The workflow will use these.
        "companyName": payload.get("companyName"),
        "filters": payload.get("filters", {})
    }

    try:
        # Note: The workflow (process_companies) is applied asynchronously inside entity_service.add_item.
        id_returned = entity_service.add_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,  # Always use this constant.
            entity=job_record,              # The initial job record.
            workflow=process_companies      # The asynchronous workflow to enrich and update the entity.
        )
    except Exception as e:
        # If there is an exception while saving, respond with error.
        return jsonify({
            "searchId": None,
            "status": "error",
            "message": f"Failed to save search job: {e}"
        }), 500

    # Return a response immediately informing the client the search is in progress.
    return SearchResponse(
        searchId=id_returned,
        status="processing",
        message="Your search job has been created and is being processed."
    )

# GET endpoint to retrieve results based on job search id.
@app.route("/companies/results/<job_id>", methods=["GET"])
async def get_search_results(job_id: str):
    """
    Retrieve the job record (search results/status) for a given search id.

    Potential issues:
    """
    try:
        job = entity_service.get_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
    except Exception as e:
        return jsonify({"error": f"Error retrieving job: {e}"}), 500

    if not job:
        return jsonify({"error": "Invalid searchId"}), 404

    # Provide appropriate responses based on the job status.
    if job.get("status") == "processing":
        return jsonify({
            "searchId": job_id,
            "status": "processing",
            "message": "Your search is still being processed, please try again later."
        }), 202

    if job.get("status") == "error":
        return jsonify({
            "searchId": job_id,
            "status": "error",
            "message": "There was an error processing your search.",
            "error": job.get("error")
        }), 500

    # If completed, include metadata and the enriched results.
    results = job.get("results", [])
    return jsonify({
        "searchId": job_id,
        "results": results,
        "metadata": {
            "requestedAt": job.get("requestedAt"),
            "completedAt": job.get("completedAt"),
            "resultCount": len(results)
        }
    }), 200

if __name__ == '__main__':
    # Run the Quart application.
    # Note: Ensure that debug/reloader settings are appropriate for your production environment.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)