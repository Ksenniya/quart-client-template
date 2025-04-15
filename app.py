from common.grpc_client.grpc_client import grpc_stream

import asyncio
import logging
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

# Initialize logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize the Quart app
app = Quart(__name__)
QuartSchema(app)

@dataclass
class InputData:
    inputData: str
    additionalParam: str

@dataclass
class ResultData:
    results: list

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

@app.route('/api/data', methods=['POST'])
@validate_request(InputData)  # Validation is performed last for POST requests
async def submit_data(data: InputData):
    entity_id = str(len(entity_job) + 1)  # Simple ID generation, can be replaced with an external call
    requested_at = request.date

    entity_data = {
        "id": entity_id,
        "status": "processing",
        "requestedAt": requested_at,
        "inputData": data.inputData,
        "additionalParam": data.additionalParam
    }

    # Add item to external service with the workflow function
    await entity_service.add_item(
        token=cyoda_token,
        entity_model="entity_job",
        entity_version=ENTITY_VERSION,
        entity=entity_data,
        )

    return jsonify({"result": "processing", "message": "Data is being processed", "id": entity_id}), 200

@app.route('/api/results', methods=['GET'])
@validate_querystring(ResultData)  # Validation is performed first for GET requests
async def get_results():
    results = await entity_service.get_items(
        token=cyoda_token,
        entity_model="entity_job",
        entity_version=ENTITY_VERSION,
    )
    return jsonify({"results": results}), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
