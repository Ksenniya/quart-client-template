#!/usr/bin/env python3
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Dataclass for POST /external-data request parameters
@dataclass
class ExternalDataParams:
    param: str = ""  # Optional parameter; available for future enhancements.

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Asynchronous workflow function for the external_data entity.
# This function is applied to the entity asynchronously before persistence.
# It fetches supplementary external data, performs processing, and updates the entity's state.
async def process_external_data(entity: dict):
    try:
        # Fetch external data from the remote API.
        async with httpx.AsyncClient() as client:
            response = await client.get("https://jsonplaceholder.typicode.com/posts/1")
            response.raise_for_status()
            fetched_data = response.json()
        # Merge the fetched data into the entity without overwriting critical properties.
        # Preserve current status if already set to failed.
        if entity.get("status") != "failed":
            entity.update(fetched_data)
            # Perform a sample business-specific calculation (dummy: length of title).
            title = fetched_data.get("title", "")
            entity["calculationResult"] = len(title)
            # Update entity status to indicate successful processing.
            entity["status"] = "completed"
            logger.info("Workflow processing completed successfully for entity requested at %s.", entity.get("requestedAt"))
        else:
            logger.warning("Entity marked as failed. Skipping further processing.")
    except Exception as e:
        # In case of any exception, mark the entity as failed.
        entity["status"] = "failed"
        logger.exception(e)
    # Return the modified entity. The new state will be persisted.
    return entity

# POST endpoint: Initiates processing via the workflow function.
# The controller now only assembles minimal entity data and delegates logic to the workflow.
@app.route('/external-data', methods=['POST'])
@validate_request(ExternalDataParams)
async def fetch_external_data(data: ExternalDataParams):
    try:
        logger.info("Received POST /external-data request with parameters: %s", data)
        # Prepare initial job data with minimal attributes.
        job_data = {
            "requestedAt": datetime.now().isoformat(),
            "param": data.param,  # Parameter can be used within the workflow for conditional processing.
            "status": "processing"  # Initial status.
        }
        # Add the job to entity_service with the workflow function.
        # The workflow function will be invoked asynchronously before persisting the entity.
        technical_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="external_data",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=job_data,  # initial entity data
            workflow=process_external_data  # Workflow function applied asynchronously.
        )
        logger.info("Created job %s with initial status 'processing'.", technical_id)
        # Return the technical id; the processed result can be retrieved via a separate endpoint.
        return jsonify({"id": technical_id, "message": "Processing started."})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500

# GET endpoint: Retrieves all results stored via the entity_service.
@app.route('/results', methods=['GET'])
async def get_results():
    try:
        logger.info("Received GET /results request")
        results = await entity_service.get_items(
            token=cyoda_token,
            entity_model="external_data",
            entity_version=ENTITY_VERSION
        )
        return jsonify({"results": results})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)