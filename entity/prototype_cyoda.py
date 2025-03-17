#!/usr/bin/env python3
import asyncio
import logging
import uuid
import datetime
import httpx
from dataclasses import dataclass

from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

# Initialize Quart app and schema
app = Quart(__name__)
QuartSchema(app)

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# Startup hook to initialize cyoda connection
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Data model for process endpoint
@dataclass
class ProcessData:
    inputData: str  # Using only primitive types

async def process_entity(job_id: str, input_data: str):
    """Process the input data and update the job status via entity_service."""
    try:
        async with httpx.AsyncClient() as client:
            # External API call to get current UTC time
            response = await client.get("http://worldtimeapi.org/api/timezone/Etc/UTC")
            response.raise_for_status()
            external_data = response.json()
        current_datetime = external_data.get("datetime")
        result = f"Processed '{input_data}' at {current_datetime}"
        update_data = {"result": result, "status": "completed"}
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="process",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=update_data,
            technical_id=job_id,
            meta={}
        )
        logger.info(f"Job {job_id} completed successfully.")
    except Exception as e:
        logger.exception(e)
        update_data = {"result": None, "status": "error"}
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="process",
            entity_version=ENTITY_VERSION,
            entity=update_data,
            technical_id=job_id,
            meta={}
        )

@app.route('/hello', methods=['GET'])
async def hello():
    """Return a simple 'Hello, World!' message."""
    return jsonify({"message": "Hello, World!"})

# For POST requests, due to an issue in quart-schema, the route decorator must precede the validate_request decorator.
@app.route('/process', methods=['POST'])
@validate_request(ProcessData)
async def process(data: ProcessData):
    """
    Accept input data, fire a background task to process it, and return a job reference.
    External data retrieval and calculations are executed in the background.
    """
    try:
        input_data = data.inputData
        if not input_data:
            return jsonify({"error": "inputData is required"}), 400

        requested_at = datetime.datetime.utcnow().isoformat()
        job_data = {
            "status": "processing",
            "requestedAt": requested_at,
            "inputData": input_data
        }
        # Create an external processing job via entity_service
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="process",  # entity_model as defined for processing jobs
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=job_data  # the validated data object
        )

        # Fire and forget the processing task
        asyncio.create_task(process_entity(job_id, input_data))

        # Return only the job_id along with initial status and requested time
        return jsonify({
            "job_id": job_id,
            "status": "processing",
            "requestedAt": requested_at
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "An error occurred during processing."}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)