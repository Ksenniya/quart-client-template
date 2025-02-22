#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import uuid
import datetime
import logging
from dataclasses import dataclass
from quart import Quart, jsonify
import aiohttp
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring

# Import constant and external services.
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Quart(__name__)
QuartSchema(app)

# Ensure that the external cyoda service is initialized on startup.
@app.before_serving
async def startup():
    try:
        await init_cyoda(cyoda_token)
        logger.info("Cyoda service initialization complete.")
    except Exception as exc:
        logger.exception("Failed to initialize cyoda service: %s", exc)
        raise

# Dataclass for POST request payload validation.
@dataclass
class CompanySearchInput:
    companyName: str
    registrationDateStart: str = ""  # Optional; expected format: yyyy-mm-dd
    registrationDateEnd: str = ""    # Optional; expected format: yyyy-mm-dd

# ------------------ Endpoint Handlers ------------------
@app.route('/companies/search', methods=['POST'])
@validate_request(CompanySearchInput)
@validate_response(dict, 200)
async def search_companies(data: CompanySearchInput):
    """
    POST endpoint to initiate a company search.
    This endpoint validates input and builds an initial record; the heavy processing
    is delegated entirely to the workflow function.
    """
    if not data.companyName.strip():
        return jsonify({"error": "companyName is required"}), 400

    # Generate a requested timestamp.
    requested_at = datetime.datetime.utcnow().isoformat()
    # Build an entity record that includes user provided parameters.
    record = {
        "status": "processing",
        "requestedAt": requested_at,
        "results": None,
        "companyName": data.companyName,
        "registrationDateStart": data.registrationDateStart,
        "registrationDateEnd": data.registrationDateEnd
    }

    try:
        # Note: The entity_service.add_item call now receives the workflow function.
        # The workflow function (process_companies_search) will be applied asynchronously,
        # updating the entity in place right before it is persisted externally.
        returned_id = entity_service.add_item(
            token=cyoda_token,
            entity_model="companies_search",
            entity_version=ENTITY_VERSION,
            entity=record,
            workflow=process_companies_search
        )
    except Exception as ex:
        logger.exception("Error adding entity item: %s", ex)
        return jsonify({"error": "Failed to add search job."}), 500

    return jsonify({
        "requestId": returned_id,
        "status": "processing",
        "message": "Your request is being processed. Use the GET endpoint with your requestId to retrieve the results."
    })

@app.route('/companies/search/<job_id>', methods=['GET'])
async def get_search_results(job_id: str):
    """
    GET endpoint to retrieve a company search result by its request (job) id.
    If the entity is not found, an error is returned.
    """
    try:
        job_record = entity_service.get_item(
            token=cyoda_token,
            entity_model="companies_search",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
    except Exception as ex:
        logger.exception("Error retrieving job %s: %s", job_id, ex)
        return jsonify({"error": "Internal error retrieving the job record."}), 500

    if not job_record:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(job_record)

# ------------------ Application Entrypoint ------------------
if __name__ == '__main__':
    # Note: threaded=True is used for development only. Consider proper async
    # server deployment for production (e.g. Hypercorn or Uvicorn).
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)