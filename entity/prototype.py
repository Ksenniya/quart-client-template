import asyncio
import logging
import uuid
import datetime
import httpx
from dataclasses import dataclass

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

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

# In-memory local cache to store processing jobs
job_store = {}

# Data model for process endpoint
@dataclass
class ProcessData:
    inputData: str  # Using only primitive types

async def process_entity(job_id: str, input_data: str):
    """Process the input data and update the job_store with the result."""
    try:
        async with httpx.AsyncClient() as client:
            # Real API call to an external service (WorldTimeAPI to get current UTC time)
            response = await client.get("http://worldtimeapi.org/api/timezone/Etc/UTC")
            response.raise_for_status()
            external_data = response.json()

        current_datetime = external_data.get("datetime")
        # TODO: Replace the following processing logic with the actual business logic as requirements become clearer.
        result = f"Processed '{input_data}' at {current_datetime}"

        # Update the local cache with result of processing
        job_store[job_id]['result'] = result
        job_store[job_id]['status'] = 'completed'
        logger.info(f"Job {job_id} completed successfully.")
    except Exception as e:
        logger.exception(e)
        job_store[job_id]['status'] = 'error'
        job_store[job_id]['result'] = None

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

        # Create a unique job identifier and store the job in local cache
        job_id = str(uuid.uuid4())
        requested_at = datetime.datetime.utcnow().isoformat()
        job_store[job_id] = {"status": "processing", "requestedAt": requested_at}

        # Fire and forget the processing task.
        asyncio.create_task(process_entity(job_id, input_data))

        return jsonify({
            "job_id": job_id,
            "status": job_store[job_id]["status"],
            "requestedAt": job_store[job_id]["requestedAt"]
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "An error occurred during processing."}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)