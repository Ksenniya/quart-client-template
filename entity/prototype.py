import asyncio
import logging
from datetime import datetime
from uuid import uuid4
from dataclasses import dataclass
from typing import List, Optional

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)  # enable QuartSchema

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

# In-memory caches (mock persistence)
pets_cache = {}
pet_id_counter = 1

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
    global pet_id_counter
    try:
        pet = data.__dict__
        pet_id = pet_id_counter
        pet["id"] = pet_id
        pets_cache[pet_id] = pet
        pet_id_counter += 1
        # Fire and forget the processing task.
        job_id = str(uuid4())
        entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
        asyncio.create_task(process_entity(entity_jobs[job_id], pet))
        return jsonify(pet)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add pet"}), 500

# Endpoint to update or delete an existing pet.
@app.route('/pets/<int:pet_id>', methods=['POST'])
@validate_request(PetAction)
async def update_or_delete_pet(pet_id, data: PetAction):
    try:
        if pet_id not in pets_cache:
            return jsonify({"error": "Pet not found"}), 404
        if data.action == "update":
            pet = pets_cache[pet_id]
            # Merge update fields if provided.
            if data.name is not None:
                pet["name"] = data.name
            if data.status is not None:
                pet["status"] = data.status
            # TODO: Merge additional fields as necessary.
            # Fire and forget the update processing task.
            job_id = str(uuid4())
            entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
            asyncio.create_task(process_entity(entity_jobs[job_id], pet))
            return jsonify(pet)
        elif data.action == "delete":
            del pets_cache[pet_id]
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