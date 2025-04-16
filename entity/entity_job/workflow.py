from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring
import logging
import asyncio

app = Quart(__name__)
QuartSchema(app)

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# In-memory cache to simulate persistence
entity_job = {}

async def process_set_status(entity_data, status):
    # Function to update the status of the entity
    entity_data['status'] = status

async def process_simulate_delay():
    # Function to simulate processing delay
    await asyncio.sleep(1)  # Simulate processing delay

@app.route('/api/hello', methods=['GET'])
@validate_querystring(HelloResponse)  # Workaround: validation first for GET requests
async def hello_world():
    return jsonify({"message": "Hello, World!"})

@app.route('/api/process', methods=['POST'])
@validate_request(ProcessRequest)  # Validation for POST requests
async def process_data(data: ProcessRequest):
    job_id = len(entity_job) + 1  # Simple ID generation
    requested_at = request.date

    # Store job details in the cache
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}

    try:
        # Fire and forget the processing task
        await asyncio.create_task(process_entity_job(entity_job[job_id]))
        return jsonify({"result": f"Job {job_id} is being processed."}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "An error occurred while processing the data."}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)