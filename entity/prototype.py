```python
import asyncio
import logging
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
import httpx

app = Quart(__name__)
QuartSchema(app)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# In-memory cache to mock persistence
entity_job = {}

# Mock function to simulate external API call
async def external_api_call(data):
    # TODO: Implement actual call to a real external API
    async with httpx.AsyncClient() as client:
        response = await client.post('https://jsonplaceholder.typicode.com/posts', json=data)
        return response.json()

# Data classes for validation
@dataclass
class HelloRequest:
    name: str  # Primitive type for name

@dataclass
class DataRequest:
    inputData: dict  # Primitive type for input data

# Route for hello endpoint
@app.route('/hello', methods=['GET'])
@validate_querystring(HelloRequest)  # Workaround: Validation first for GET requests
async def hello():
    name = request.args.get('name', 'World')
    return jsonify({"message": f"Hello, {name}!"})

# Route for data endpoint
@app.route('/data', methods=['POST'])
@validate_request(DataRequest)  # Validation second for POST requests
async def data(data: DataRequest):
    job_id = str(len(entity_job) + 1)  # Simple ID generation
    requested_at = request.json.get('requestedAt', None)  # Optional timestamp

    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}
    logger.info(f"Job {job_id} started.")

    # Fire and forget the processing task
    await asyncio.create_task(process_entity(job_id, data.inputData))
    return jsonify({"status": "success", "job_id": job_id}), 202

# Function to process the entity asynchronously
async def process_entity(job_id, data):
    try:
        # Simulate processing
        result = await external_api_call(data)  # Placeholder for external API call
        entity_job[job_id]["status"] = "completed"
        logger.info(f"Job {job_id} completed with result: {result}")
    except Exception as e:
        logger.exception(e)
        entity_job[job_id]["status"] = "error"

# Route for results endpoint
@app.route('/results', methods=['GET'])
async def results():
    return jsonify({"results": entity_job})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```