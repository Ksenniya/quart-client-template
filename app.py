from common.grpc_client.grpc_client import grpc_stream

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass
import logging
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token
import asyncio

app = Quart(__name__)
QuartSchema(app)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

@dataclass
class GreetRequest:
    name: str

@app.route('/hello', methods=['GET'])
async def hello():
    return jsonify({"message": "Hello, World!"})

@app.route('/greet', methods=['POST'])
@validate_request(GreetRequest)  # Validation for POST must come last
async def greet(data: GreetRequest):
    name = data.name

    if not name:
        return jsonify({"error": "Name is required."}), 400

    # Prepare the entity data
    entity_data = {"name": name}

    # Add item to external service and return the id
    try:
        id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="greeting",
            entity_version=ENTITY_VERSION,
            entity=entity_data,
            )
    except Exception as e:
        logger.error(f"Failed to add item: {e}")
        return jsonify({"error": "Failed to process the request."}), 500

    return jsonify({"message": f"Hello, {name}!", "id": id})

@app.route('/greet_by_query', methods=['GET'])
@validate_querystring(GreetRequest)  # Workaround issue: Validation must come first for GET
async def greet_by_query():
    name = request.args.get('name')  # Standard approach to access parameters for GET requests

    if not name:
        return jsonify({"error": "Name is required."}), 400

    # Prepare the entity data
    entity_data = {"name": name}

    # Add item to external service and return the id
    try:
        id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="greeting",
            entity_version=ENTITY_VERSION,
            entity=entity_data,
            )
    except Exception as e:
        logger.error(f"Failed to add item: {e}")
        return jsonify({"error": "Failed to process the request."}), 500

    return jsonify({"message": f"Hello, {name}!", "id": id})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
