```python
from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring
import logging
import asyncio
from datetime import datetime
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@dataclass
class InputData:
    inputData: str

@dataclass
class QueryData:
    name: str

async def process_entity_name(entity):
    # Example workflow function to process the entity
    entity['processed'] = True  # Modify entity as needed before persistence

    # Fire and forget async task example
    try:
        secondary_data = await fetch_secondary_data(entity['inputData'])
        entity['secondaryData'] = secondary_data
    except Exception as e:
        logger.error(f"Failed to fetch secondary data: {e}")

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

    # Prepare the entity data
    entity_data = {"inputData": input_data}  # Wrap in appropriate entity format

    # Add item to external service
    try:
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="entity_name",  # Replace with actual entity name
            entity_version=ENTITY_VERSION,
            entity=entity_data,  # Pass the prepared entity data
            workflow=process_entity_name  # Pass the workflow function
        )
        return jsonify({"jobId": job_id, "status": "processing"}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to process data"}), 500

@app.route("/test", methods=["GET"])
@validate_querystring(QueryData)  # Validation should be first in GET
async def get_todo():
    name = request.args.get('name')  # Access parameters using standard approach
    return jsonify({"name": name})

@app.route("/companies/<string:id>/lei", methods=["GET"])
async def get_lei(id: str):
    # Data retrieval from external service
    try:
        lei_data = await entity_service.get_item(
            token=cyoda_token,
            entity_model="entity_name",  # Replace with actual entity name
            entity_version=ENTITY_VERSION,
            technical_id=id
        )
        return jsonify(lei_data), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve LEI data"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```