```python
from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring
import httpx
import asyncio
import logging
from datetime import datetime

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# In-memory cache for job status
entity_job = {}

@dataclass
class InputData:
    inputData: str

@dataclass
class QueryData:
    name: str

async def fetch_external_data(input_data):
    # TODO: Replace this mock with a real external API call
    await asyncio.sleep(1)  # Simulate network delay
    return {"externalSourceData": f"Processed external data for {input_data}"}

async def process_entity(job_id, input_data):
    # Simulate processing task
    await asyncio.sleep(2)  # Simulate a processing delay
    try:
        external_data = await fetch_external_data(input_data)
        entity_job[job_id]["status"] = "completed"
        entity_job[job_id]["result"] = external_data
    except Exception as e:
        logger.error(f"Error processing entity: {e}")
        entity_job[job_id]["status"] = "failed"

@app.route('/hello', methods=['GET'])
@validate_querystring(QueryData)  # Validation should be first in GET
async def hello():
    name = request.args.get('name')  # Access parameters using standard approach
    return jsonify({"message": f"Hello, {name if name else 'World!'}!"})

@app.route('/process', methods=['POST'])
@validate_request(InputData)  # Validation should be last in POST
async def process(data: InputData):
    input_data = data.inputData
    
    if not input_data:
        return jsonify({"error": "Invalid input data"}), 400

    job_id = len(entity_job) + 1  # Simple job ID generation
    requested_at = datetime.now()

    # Initialize job status
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}
    
    # Fire and forget the processing task
    await asyncio.create_task(process_entity(job_id, input_data))

    return jsonify({"jobId": job_id, "status": "processing"}), 200

@app.route("/companies/<string:id>/lei", methods=["GET"])
async def get_lei(id: str):
    # No validation needed for this endpoint
    return jsonify({"lei": f"LEI data for company {id}"})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```