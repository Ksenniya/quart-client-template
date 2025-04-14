```python
import asyncio
import logging
from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

app = Quart(__name__)
QuartSchema(app)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@dataclass
class InputData:
    inputData: list

async def process_calculate_job(entity_data):
    # Placeholder for processing logic
    # Example: Modify the entity state or add related entities
    return entity_data  # Return modified entity data

@app.route('/hello', methods=['GET'])
async def hello_world():
    return jsonify({"message": "Hello, World!"})

@app.route('/calculate', methods=['POST'])
@validate_request(InputData)  # Validation is placed last for POST requests
async def calculate(data: InputData):
    input_data = data.inputData
    
    if len(input_data) != 2:
        return jsonify({"error": "Invalid input data. Expected two numbers."}), 400
    
    # Call to external service to add the item
    try:
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="calculate_job",
            entity_version=ENTITY_VERSION,
            entity=data.inputData,
            workflow=process_calculate_job  # Adding the workflow function
        )
        return jsonify({"jobId": job_id, "status": "processing"}), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to process the job."}), 500

@app.route('/companies/<string:id>/lei', methods=['GET'])
async def get_lei(id: str):
    try:
        # Call to external service to retrieve LEI
        lei_data = await entity_service.get_item(
            token=cyoda_token,
            entity_model="lei",
            entity_version=ENTITY_VERSION,
            technical_id=id
        )
        return jsonify(lei_data), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve LEI."}), 500

@app.route('/test', methods=['GET'])
@validate_querystring(InputData)  # Validation is placed first for GET requests (workaround)
async def get_todo():
    name = request.args.get('name')
    return jsonify({"name": name})  # Response based on query parameter

@app.route('/test', methods=['POST'])
@validate_request(InputData)  # Validation is placed last for POST requests
async def create_todo(data: InputData):
    return jsonify({"inputData": data.inputData})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```