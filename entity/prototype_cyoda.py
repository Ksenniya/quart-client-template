import asyncio
import logging
import uuid
from datetime import datetime
from dataclasses import dataclass

import httpx
from quart import Quart, jsonify, request
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
    param: str = ""  # Optional parameter for transformation/calculation; default value used if not provided.

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Asynchronous processing function for the external data.
# It performs a dummy calculation (length of title) and updates the job record via the external entity_service.
async def process_entity(technical_id: str, data: dict):
    try:
        # Perform business-specific calculation (dummy: length of title)
        calculation_result = len(data.get("title", ""))
        data["calculationResult"] = calculation_result
        data["status"] = "completed"
        # Update the job record with the processed data
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="external_data",
            entity_version=ENTITY_VERSION,
            entity=data,
            technical_id=technical_id,
            meta={}
        )
        logger.info(f"Job {technical_id} completed processing.")
    except Exception as e:
        logger.exception(e)
        try:
            # On failure, update the job record to indicate failure.
            await entity_service.update_item(
                token=cyoda_token,
                entity_model="external_data",
                entity_version=ENTITY_VERSION,
                entity={"status": "failed"},
                technical_id=technical_id,
                meta={}
            )
        except Exception as inner_e:
            logger.exception(inner_e)

# POST endpoint: Fetch external data and trigger asynchronous processing.
# Instead of interacting with a local in-memory cache, the job is added via entity_service.add_item.
@app.route('/external-data', methods=['POST'])
@validate_request(ExternalDataParams)
async def fetch_external_data(data: ExternalDataParams):
    try:
        logger.info("Received POST /external-data request with parameters: %s", data)
        # Fetch external data using httpx.AsyncClient
        async with httpx.AsyncClient() as client:
            response = await client.get("https://jsonplaceholder.typicode.com/posts/1")
            response.raise_for_status()
            external_data = response.json()
        logger.info("Fetched external data successfully.")

        # Prepare job data with an initial status and request time.
        job_data = external_data.copy()
        job_data["status"] = "processing"
        job_data["requestedAt"] = datetime.now().isoformat()

        # Add the job to the external entity service and get the technical id.
        technical_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="external_data",
            entity_version=ENTITY_VERSION,
            entity=job_data
        )
        logger.info("Created job %s with status 'processing'.", technical_id)

        # Fire-and-forget asynchronous processing task.
        asyncio.create_task(process_entity(technical_id, external_data))

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