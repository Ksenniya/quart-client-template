#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_response
import aiohttp

# Import external service objects and configuration constants.
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

# Configure logging to capture errors and info.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Quart(__name__)
QuartSchema(app)  # Initialize request/response validation


# -------------------------------------------------------------------------
# Startup: Initialize any external systems before serving requests.
# -------------------------------------------------------------------------
@app.before_serving
async def startup():
    try:
        await init_cyoda(cyoda_token)
        logger.info("Cyoda successfully initialized.")
    except Exception as e:
        logger.error("Failed to initialize cyoda: %s", str(e))
        # Depending on your policy, you might choose to re‐raise here


# -------------------------------------------------------------------------
# Data Models for API validation.
# -------------------------------------------------------------------------
@dataclass
class EnrichRequest:
    companyName: str
    outputFormat: str = "json"  # Default format


@dataclass
class EnrichResponse:
    jobId: str
    message: str


# -------------------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------------------
@app.route("/companies/enrich", methods=["POST"])
@validate_request(EnrichRequest)
@validate_response(EnrichResponse, 202)
async def enrich_companies(data: EnrichRequest):
    """
    Initiates company data enrichment. The endpoint performs minimal work by building
    a job record that contains:

    The enrichment work is delegated entirely to the workflow function (process_companies)
    which is invoked asynchronously before the entity is persisted.
    """
    requested_at = datetime.utcnow().isoformat()
    job_data = {
        "status": "queued",
        "requestedAt": requested_at,
        "results": None,
        "input": data.__dict__  # store the original request for later use.
    }

    # Persist the job record and ensure the workflow function is applied.
    try:
        job_id = entity_service.add_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=job_data,
            workflow=process_companies  # enforce pre-persistence enrichment via workflow
        )
    except Exception as e:
        logger.exception("Failed to add job item:")
        return jsonify({"error": "Failed to create job", "details": str(e)}), 500

    return jsonify({
        "jobId": job_id,
        "message": "Enrichment processing started. Use the jobId to retrieve results."
    }), 202


@app.route("/companies/results/<job_id>", methods=["GET"])
async def get_results(job_id: str):
    """
    Retrieves the enriched result of a given job id. If the job is still processing,
    a relevant message is returned; if enrichment failed, then the error is provided.
    """
    try:
        job = entity_service.get_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
    except Exception as e:
        logger.exception("Error getting job item:")
        return jsonify({"error": "Error retrieving job", "details": str(e)}), 500

    if not job:
        return jsonify({"error": "Job not found"}), 404

    status = job.get("status", "unknown")
    if status not in ["completed", "failed"]:
        return jsonify({
            "jobId": job_id,
            "status": status,
            "message": "Results are not ready yet."
        }), 202

    if status == "failed":
        return jsonify({
            "jobId": job_id,
            "status": status,
            "error": job.get("error", "Unknown error occurred."),
            "message": "Enrichment process failed."
        }), 500

    # Otherwise, the job is completed.
    return jsonify({
        "jobId": job_id,
        "results": job.get("results", [])
    }), 200


# -------------------------------------------------------------------------
# Main block to run the app.
# -------------------------------------------------------------------------
if __name__ == '__main__':
    # Using threaded=True to ensure asynchronous background tasks execute properly in this prototype.
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)