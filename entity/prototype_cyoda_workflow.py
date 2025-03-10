#!/usr/bin/env python3
import asyncio
import uuid
import datetime
import logging
import httpx

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass

# External service functions and configurations
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Constant for the entity model name used across external service calls
ENTITY_MODEL = "entity/prototype"

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Data models for request validation
@dataclass
class FetchDataRequest:
    external_api: str  # Expected to be "petstore"

@dataclass
class ResultsQuery:
    fetch_id: str

# Workflow function applied to the entity before persistence.
# Function name must have the prefix 'process_' followed by the entity name: in this case, 'prototype'.
async def process_prototype(entity):
    # Apply any needed transformations to the entity before it is persisted.
    # For example, add a flag indicating that the workflow processing has been applied.
    entity["workflow_applied"] = True
    return entity

# Background processing function that retrieves external data and updates the job via entity_service
async def process_entity(job_id: str, request_data: dict):
    """
    Process the entity: fetch data from external API and update the job status.
    Additional business specific transformations can be added here.
    """
    external_api_url = "https://petstore.swagger.io/v2/swagger.json"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(external_api_url)
            response.raise_for_status()
            data = response.json()
        # Prepare update payload with fetched data and mark job as completed.
        updated_entity = {
            "data": data,
            "status": "completed"
        }
        await entity_service.update_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=updated_entity,
            technical_id=job_id,
            meta={}
        )
        logger.info(f"Job {job_id} completed successfully.")
    except Exception as e:
        logger.exception(e)
        failed_entity = {
            "status": "failed",
            "error": str(e)
        }
        try:
            await entity_service.update_item(
                token=cyoda_token,
                entity_model=ENTITY_MODEL,
                entity_version=ENTITY_VERSION,
                entity=failed_entity,
                technical_id=job_id,
                meta={}
            )
        except Exception as inner_e:
            logger.exception(inner_e)

# POST /fetch-data endpoint to initiate data fetching process.
@app.route('/fetch-data', methods=['POST'])
@validate_request(FetchDataRequest)
async def fetch_data(data: FetchDataRequest):
    """
    POST /fetch-data:
    Initiates the process to fetch external data and perform business logic.
    """
    if data.external_api.lower() != "petstore":
        return jsonify({"error": "Unsupported external_api value. Expected 'petstore'."}), 400

    # Create initial job entity with processing status.
    requested_at = datetime.datetime.utcnow().isoformat()
    job_entity = {
        "status": "processing",
        "requestedAt": requested_at
    }
    try:
        # Call external service to add the job entity.
        # Pass workflow function process_prototype so that it is applied before persistence.
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=job_entity,
            workflow=process_prototype
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to initiate job"}), 500

    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, data.__dict__))

    return jsonify({
        "fetch_id": job_id,
        "status": "success",
        "message": "Data fetching initiated successfully."
    })

# GET /results endpoint to retrieve results of a previously initiated job.
@validate_querystring(ResultsQuery)
@app.route('/results', methods=['GET'])
async def get_results():
    """
    GET /results:
    Retrieves the processed data for a previously initiated job.
    """
    fetch_id = request.args.get('fetch_id')
    if not fetch_id:
        return jsonify({"error": "Missing fetch_id"}), 400
    try:
        result = await entity_service.get_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            technical_id=fetch_id
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Error retrieving job result"}), 500

    if result is None:
        return jsonify({"error": "Invalid fetch_id or job not found"}), 400

    return jsonify({
        "fetch_id": fetch_id,
        "status": result.get("status", "unknown"),
        "data": result.get("data", {})
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)