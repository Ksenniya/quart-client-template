from common.grpc_client.grpc_client import grpc_stream
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

@dataclass
class ExternalDataParams:
    param: str = ""  # Optional parameter; available for future enhancements.

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

# POST endpoint: Add a new pet store entity
@app.route('/pet-store', methods=['POST'])
@validate_request(ExternalDataParams)
async def add_pet_store(data: ExternalDataParams):
    try:
        logger.info("Received POST /pet-store request with parameters: %s", data)
        pet_store_data = {
            "requestedAt": datetime.now().isoformat(),
            "param": data.param,
            "status": "processing"  # Initial status.
        }
        technical_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="pet_store",
            entity_version=ENTITY_VERSION,
            entity=pet_store_data,
        )
        logger.info("Created pet store %s with initial status 'processing'.", technical_id)
        return jsonify({"id": technical_id, "message": "Pet store creation started."})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500

# GET endpoint: Retrieve a specific pet store entity by ID
@app.route('/pet-store/<id>', methods=['GET'])
async def get_pet_store(id):
    try:
        logger.info("Received GET /pet-store/%s request", id)
        pet_store = await entity_service.get_item(
            token=cyoda_token,
            entity_model="pet_store",
            entity_version=ENTITY_VERSION,
            technical_id=id,
        )
        return jsonify({"pet_store": pet_store})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500

# GET endpoint: Retrieve all pet store entities
@app.route('/pet-stores', methods=['GET'])
async def get_pet_stores():
    try:
        logger.info("Received GET /pet-stores request")
        pet_stores = await entity_service.get_items(
            token=cyoda_token,
            entity_model="pet_store",
            entity_version=ENTITY_VERSION,
        )
        return jsonify({"pet_stores": pet_stores})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500

# PUT endpoint: Update a specific pet store entity by ID
@app.route('/pet-store/<id>', methods=['PUT'])
@validate_request(ExternalDataParams)
async def update_pet_store(id, data: ExternalDataParams):
    try:
        logger.info("Received PUT /pet-store/%s request with parameters: %s", id, data)
        pet_store_data = {
            "requestedAt": datetime.now().isoformat(),
            "param": data.param,
            "status": "updated",
        }
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="pet_store",
            entity_version=ENTITY_VERSION,
            entity=pet_store_data,
            technical_id=id,
            meta={},
        )
        return jsonify({"message": "Pet store updated successfully."})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500

# DELETE endpoint: Delete a specific pet store entity by ID
@app.route('/pet-store/<id>', methods=['DELETE'])
async def delete_pet_store(id):
    try:
        logger.info("Received DELETE /pet-store/%s request", id)
        await entity_service.delete_item(
            token=cyoda_token,
            entity_model="pet_store",
            entity_version=ENTITY_VERSION,
            technical_id=id,
            meta={},
        )
        return jsonify({"message": "Pet store deleted successfully."})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)