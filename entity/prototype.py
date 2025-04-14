```python
import asyncio
import logging
from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

app = Quart(__name__)
QuartSchema(app)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Local cache for jobs
entity_job = {}

@dataclass
class InputData:
    inputData: list

async def process_entity(job_id, input_data):
    # TODO: Replace with actual processing logic
    await asyncio.sleep(2)  # Simulate processing delay
    logger.info(f"Processing job {job_id} with input data: {input_data}")
    entity_job[job_id]["status"] = "completed"

@app.route('/hello', methods=['GET'])
async def hello_world():
    return jsonify({"message": "Hello, World!"})

@app.route('/calculate', methods=['POST'])
@validate_request(InputData)  # Validation is placed last for POST requests
async def calculate(data: InputData):
    input_data = data.inputData
    
    if len(input_data) != 2:
        return jsonify({"error": "Invalid input data. Expected two numbers."}), 400
    
    job_id = f"job_{len(entity_job) + 1}"
    requested_at = asyncio.get_event_loop().time()
    
    # Store job information
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}
    
    # Fire and forget processing task
    await asyncio.create_task(process_entity(job_id, input_data))
    
    return jsonify({"jobId": job_id, "status": "processing"}), 202

@app.route('/companies/<string:id>/lei', methods=['GET'])
async def get_lei(id: str):
    # Placeholder for actual LEI retrieval logic
    return jsonify({"id": id, "lei": "mock-lei-value"})

@app.route('/test', methods=['GET'])
@validate_querystring(InputData)  # Validation is placed first for GET requests (workaround)
async def get_todo():
    # Access GET request parameters
    name = request.args.get('name')
    return jsonify({"name": name})  # Response based on query parameter

@app.route('/test', methods=['POST'])
@validate_request(InputData)  # Validation is placed last for POST requests
async def create_todo(data: InputData):
    return jsonify({"inputData": data.inputData})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```