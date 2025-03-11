from common.grpc_client.grpc_client import grpc_stream
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
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

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