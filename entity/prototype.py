```python
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass
import httpx
import logging
import asyncio
from datetime import datetime

app = Quart(__name__)
QuartSchema(app)

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# In-memory cache for mock data persistence
entity_job = {}

# Dataclasses for validation
@dataclass
class Greeting:
    name: str

@dataclass
class Calculation:
    operation: str
    numbers: list

@dataclass
class DataRequest:
    query: str

# Mock function for external API call
async def fetch_external_data(query):
    # TODO: Replace with a real API call when requirements are clearer
    async with httpx.AsyncClient() as client:
        response = await client.get('https://jsonplaceholder.typicode.com/posts')
        return response.json() if response.status_code == 200 else []

@app.route('/hello', methods=['GET'])
@validate_querystring(Greeting)  # Workaround: validation first for GET requests
async def hello():
    name = request.args.get('name', 'World')
    return jsonify({"message": f"Hello, {name}!"})

@app.route('/calculate', methods=['POST'])
@validate_request(Calculation)  # Validation last for POST requests
async def calculate(data: Calculation):
    operation = data.operation
    numbers = data.numbers

    if operation == "add":
        result = sum(numbers)
        return jsonify({"result": result})
    else:
        return jsonify({"error": "Unsupported operation"}), 400

@app.route('/data', methods=['POST'])
@validate_request(DataRequest)  # Validation last for POST requests
async def data(data: DataRequest):
    query = data.query
    fetched_data = await fetch_external_data(query)
    # TODO: Process fetched data as needed
    return jsonify({"data": fetched_data})

@app.route('/process_job', methods=['POST'])
@validate_request(DataRequest)  # Validation last for POST requests
async def process_job(data: DataRequest):
    job_id = len(entity_job) + 1  # Simple job ID assignment
    requested_at = datetime.utcnow()

    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}
    
    # Fire and forget the processing task
    await asyncio.create_task(process_entity(entity_job[job_id], data))
    return jsonify({"job_id": job_id, "status": "processing"})

async def process_entity(job, data):
    try:
        # TODO: Implement the actual processing logic
        await asyncio.sleep(5)  # Simulate processing time
        job["status"] = "completed"
        logger.info(f"Job {data} completed successfully.")
    except Exception as e:
        job["status"] = "failed"
        logger.exception(e)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```