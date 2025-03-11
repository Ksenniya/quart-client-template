from common.grpc_client.grpc_client import grpc_stream
import asyncio
import logging
from datetime import datetime
from uuid import uuid4
from dataclasses import dataclass
from typing import List, Optional

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)  # enable QuartSchema

# Startup initialization
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task
    except Exception as e:
        logger.exception("Failed to initialize cyoda: %s", e)
        raise

# Dataclasses for request validation

@dataclass
class PetFetchRequest:
    # For POST, @validate_request must be the second decorator due to the library issue.
    status: Optional[List[str]] = None

@dataclass
class PetInput:
    # Minimal pet input validation using only primitives.
    name: str
    status: str

@dataclass
class PetAction:
    # Action must be provided: 'update' or 'delete'
    action: str
    # Optional fields for update action.
    name: Optional[str] = None
    status: Optional[str] = None
    # Additional fields can be added if needed.

@dataclass
class UserLogin:
    username: str
    password: str

# Endpoint to fetch pets from external API based on status.
@app.route('/pets/fetch', methods=['POST'])
@validate_request(PetFetchRequest)
async def fetch_pets(data: PetFetchRequest):
    try:
        statuses = data.status if data.status is not None else ["available"]
        # Prepare query parameters for the external API.
        params = [("status", status) for status in statuses]
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://petstore.swagger.io/v2/pet/findByStatus",
                params=params,
                timeout=10.0
            )
            response.raise_for_status()
            pets = response.json()
        return jsonify({"pets": pets})
    except Exception as e:
        logger.exception("Failed to fetch pets: %s", e)
        return jsonify({"error": "Failed to fetch pets"}), 500

# Endpoint to add a new pet.
@app.route('/pets', methods=['POST'])
@validate_request(PetInput)
async def add_pet(data: PetInput):
    try:
        pet = data.__dict__
        # The workflow function will process the pet asynchronously before persistence.
        new_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="pet",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=pet,
            )
        return jsonify({"id": new_id})
    except Exception as e:
        logger.exception("Failed to add pet: %s", e)
        return jsonify({"error": "Failed to add pet"}), 500

# Endpoint to update or delete an existing pet.
@app.route('/pets/<int:pet_id>', methods=['POST'])
@validate_request(PetAction)
async def update_or_delete_pet(pet_id, data: PetAction):
    try:
        # Retrieve pet from external service.
        pet = await entity_service.get_item(
            token=cyoda_token,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
        if not pet:
            return jsonify({"error": "Pet not found"}), 404

        if data.action == "update":
            # Merge update fields if provided.
            if data.name is not None:
                pet["name"] = data.name
            if data.status is not None:
                pet["status"] = data.status
            # Process pet changes using the workflow function before persistence.
            await process_pet(pet)
            await entity_service.update_item(
                token=cyoda_token,
                entity_model="pet",
                entity_version=ENTITY_VERSION,  # always use this constant
                entity=pet,
                technical_id=pet_id,  # technical_id is required
                meta={}
            )
            return jsonify(pet)
        elif data.action == "delete":
            await entity_service.delete_item(
                token=cyoda_token,
                entity_model="pet",
                entity_version=ENTITY_VERSION,  # always use this constant
                technical_id=pet_id,
                meta={}
            )
            return jsonify({"message": "Pet deleted successfully"})
        else:
            return jsonify({"error": "Invalid action provided. Use 'update' or 'delete'."}), 400
    except Exception as e:
        logger.exception("Failed to process pet update/delete: %s", e)
        return jsonify({"error": "Failed to process pet update/delete"}), 500

# Endpoint to perform user login.
@app.route('/user/login', methods=['POST'])
@validate_request(UserLogin)
async def user_login(data: UserLogin):
    try:
        if not data.username or not data.password:
            return jsonify({"error": "Username and password are required"}), 400
        params = {"username": data.username, "password": data.password}
        async with httpx.AsyncClient() as client:
            # External API expects GET with query parameters for login.
            response = await client.get(
                "https://petstore.swagger.io/v2/user/login",
                params=params,
                timeout=10.0
            )
            response.raise_for_status()
            message = response.text
        return jsonify({"token": message})
    except Exception as e:
        logger.exception("User login failed: %s", e)
        return jsonify({"error": "User login failed"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)