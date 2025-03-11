#!/usr/bin/env python3
import asyncio
import logging
from datetime import datetime
from uuid import uuid4
from dataclasses import dataclass
from typing import List, Optional

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
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
    # TODO: Add additional fields (e.g., category, photoUrls, tags) if necessary.

@dataclass
class UserLogin:
    username: str
    password: str

# In-memory job cache for asynchronous processing (mock)
entity_jobs = {}

async def process_entity(job, data):
    try:
        # TODO: Replace with actual processing logic if needed.
        await asyncio.sleep(2)  # simulate some processing time
        job["status"] = "completed"
        logger.info(f"Processed entity: {data}")
    except Exception as e:
        job["status"] = "failed"
        logger.exception(e)

# Workflow function for pet entity; must be named with prefix process_ followed by entity name.
async def process_pet(pet):
    try:
        # Simulate asynchronous processing before persistence.
        await asyncio.sleep(1)  # simulate processing delay
        # Modify the pet entity state as needed before persistence.
        pet["workflowProcessedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Workflow processing completed for pet: {pet}")
    except Exception as e:
        logger.exception(e)
        raise

# Endpoint to fetch pets from external API based on status.
# For POST endpoints, order is: @app.route first, then @validate_request.
@app.route('/pets/fetch', methods=['POST'])
@validate_request(PetFetchRequest)
async def fetch_pets(data: PetFetchRequest):
    try:
        statuses = data.status if data.status is not None else ["available"]
        # Prepare query params: Petstore API accepts multiple status parameters.
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
        logger.exception(e)
        return jsonify({"error": "Failed to fetch pets"}), 500

# Endpoint to add a new pet.
@app.route('/pets', methods=['POST'])
@validate_request(PetInput)
async def add_pet(data: PetInput):
    try:
        pet = data.__dict__
        new_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="pet",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=pet,
            workflow=process_pet  # Workflow function applied to the pet before persistence.
        )
        # Fire and forget the processing task.
        job_id = str(uuid4())
        entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
        asyncio.create_task(process_entity(entity_jobs[job_id], pet))
        return jsonify({"id": new_id})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add pet"}), 500

# Endpoint to update or delete an existing pet.
@app.route('/pets/<int:pet_id>', methods=['POST'])
@validate_request(PetAction)
async def update_or_delete_pet(pet_id, data: PetAction):
    try:
        # Retrieve pet from external service
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
            # TODO: Merge additional fields as necessary.
            await entity_service.update_item(
                token=cyoda_token,
                entity_model="pet",
                entity_version=ENTITY_VERSION,  # always use this constant
                entity=pet,
                technical_id=pet_id,  # technical_id is required
                meta={}
            )
            # Fire and forget the update processing task.
            job_id = str(uuid4())
            entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
            asyncio.create_task(process_entity(entity_jobs[job_id], pet))
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
        logger.exception(e)
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
            # External API expects GET, so use GET here with query parameters.
            response = await client.get(
                "https://petstore.swagger.io/v2/user/login",
                params=params,
                timeout=10.0
            )
            response.raise_for_status()
            message = response.text
        return jsonify({"token": message})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "User login failed"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)