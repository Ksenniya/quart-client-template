import asyncio
import logging
import uuid
from datetime import datetime
from dataclasses import dataclass

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Dataclass for POST /external-data request parameters
@dataclass
class ExternalDataParams:
    # Optional parameter for transformation/calculation; default value used if not provided.
    param: str = ""

# In-memory storage mocks
entity_job = {}         # Stores job statuses
processed_results = []  # Stores processed data results

# Asynchronous processing function for the external data
async def process_entity(job_id: str, data: dict):
    try:
        # TODO: Replace this with actual business-specific calculations/transformations as requirements evolve.
        # For example, calculating the length of the title as a dummy computed value.
        calculation_result = len(data.get("title", ""))
        data["calculationResult"] = calculation_result

        # Store the processed data in local cache (simulated persistence)
        processed_results.append(data)

        # Update the job status
        entity_job[job_id]["status"] = "completed"
        logger.info(f"Job {job_id} completed processing.")
    except Exception as e:
        logger.exception(e)
        entity_job[job_id]["status"] = "failed"

# For POST endpoints, remember to place the route decorator first, then the validation decorator.
# This is a workaround for an issue in quart-schema.
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

        # Create a job ID and record the processing status
        job_id = str(uuid.uuid4())
        requested_at = datetime.now().isoformat()
        entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}
        logger.info("Created job %s with status 'processing'.", job_id)

        # Fire-and-forget asynchronous processing task.
        asyncio.create_task(process_entity(job_id, external_data))

        return jsonify({"job_id": job_id, "message": "Processing started."})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500

# GET endpoint without request parameters does not require validation.
@app.route('/results', methods=['GET'])
async def get_results():
    try:
        logger.info("Received GET /results request")
        return jsonify({"results": processed_results})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)