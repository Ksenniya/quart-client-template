from common.grpc_client.grpc_client import grpc_stream
import asyncio
import logging
import datetime
import httpx
from dataclasses import dataclass

from quart import Quart, jsonify
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
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Startup hook to initialize cyoda connection
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

# Data model for process endpoint
@dataclass
class ProcessData:
    inputData: str  # Using only primitive types

@app.route('/hello', methods=['GET'])
async def hello():
    # Return a simple 'Hello, World!' message.
    return jsonify({"message": "Hello, World!"})

# For POST requests, due to an issue in quart-schema,
# the route decorator must precede the validate_request decorator.
@app.route('/process', methods=['POST'])
@validate_request(ProcessData)
async def process(data: ProcessData):
    """
    Accept input data, create a processing job with minimal endpoint logic,
    and offload all asynchronous tasks to the workflow function.
    The workflow function (process_process) will be invoked asynchronously
    before persisting the entity.
    """
    try:
        input_data = data.inputData
        if not input_data:
            return jsonify({"error": "inputData is required"}), 400

        requested_at = datetime.datetime.utcnow().isoformat()
        # Prepare the initial job data.
        job_data = {
            "status": "processing",
            "requestedAt": requested_at,
            "inputData": input_data
        }
        # Create a processing job via entity_service with a workflow function.
        # The workflow function performs all asynchronous tasks and updates the entity state.
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="process",  # defined for processing jobs
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=job_data,  # the validated data object
            )

        # Return only the job_id along with initial details.
        return jsonify({
            "job_id": job_id,
            "status": job_data.get("status"),
            "requestedAt": requested_at
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "An error occurred during processing."}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)