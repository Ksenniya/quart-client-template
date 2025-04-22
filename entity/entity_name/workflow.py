from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring
import logging
import asyncio
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

async def fetch_secondary_data(input_data):
    # Simulated async function to fetch secondary data
    await asyncio.sleep(1)  # Simulate a network call
    return f"Fetched secondary data for {input_data}"

@app.route('/hello', methods=['GET'])
async def hello():
    return jsonify({"message": "Hello, World!"})

@app.route('/process', methods=['POST'])
@validate_request(InputData)  # Validation should be last in POST
async def process(data: InputData):
    input_data = data.inputData
    
    if not input_data:
        return jsonify({"error": "Invalid input data"}), 400

    job_id = len(entity_job) + 1  # Simple job ID generation
    requested_at = datetime.now()

    # Initialize job status
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at, "inputData": input_data}
    
    # Fire and forget the processing task
    await asyncio.create_task(process_entity_name(entity_job[job_id]))

    return jsonify({"jobId": job_id, "status": "processing"}), 200

# Workaround for validation order issue in GET requests
@app.route("/test", methods=["GET"])
@validate_querystring(QueryData)  # Validation should be first in GET
async def get_todo():
    name = request.args.get('name')  # Access parameters using standard approach
    return jsonify({"name": name})

@app.route("/companies/<string:id>/lei", methods=["GET"])
async def get_lei(id: str):
    # No validation needed for this endpoint
    return jsonify({"lei": f"LEI data for company {id}"})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)