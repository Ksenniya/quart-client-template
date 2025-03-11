import asyncio
import logging
from datetime import datetime
from uuid import uuid4

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)  # enable QuartSchema

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


@app.route('/pets/fetch', methods=['POST'])
async def fetch_pets():
    """
    Fetches pets from the external Petstore API based on provided statuses.
    Business logic: This POST endpoint retrieves data from the external API.
    """
    try:
        req_data = await request.get_json()
        statuses = req_data.get("status", ["available"])
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


@app.route('/pets', methods=['POST'])
async def add_pet():
    """
    Adds a new pet. The pet information is stored in local cache.
    A background processing task is initiated (fire and forget).
    """
    global pet_id_counter
    try:
        pet = await request.get_json()
        pet_id = pet_id_counter
        pet["id"] = pet_id
        pets_cache[pet_id] = pet
        pet_id_counter += 1

        # Simulate processing task asynchronously
        job_id = str(uuid4())
        entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
        asyncio.create_task(process_entity(entity_jobs[job_id], pet))

        return jsonify(pet)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add pet"}), 500


@app.route('/pets/<int:pet_id>', methods=['POST'])
async def update_or_delete_pet(pet_id):
    """
    Updates or deletes an existing pet from local cache.
    The request JSON must include an "action" key with value "update" or "delete".
    For update, include the fields to update (e.g. 'name', 'status').
    For delete, only the action is necessary.
    """
    try:
        req_data = await request.get_json()
        action = req_data.get("action")
        if pet_id not in pets_cache:
            return jsonify({"error": "Pet not found"}), 404

        if action == "update":
            # Update pet details (mock update). Merge provided data.
            pet = pets_cache[pet_id]
            pet.update({k: v for k, v in req_data.items() if k in ["name", "status", "category", "photoUrls", "tags"]})
            # Simulate background processing task for the update
            job_id = str(uuid4())
            entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
            asyncio.create_task(process_entity(entity_jobs[job_id], pet))
            return jsonify(pet)

        elif action == "delete":
            del pets_cache[pet_id]
            return jsonify({"message": "Pet deleted successfully"})

        else:
            return jsonify({"error": "Invalid action provided. Use 'update' or 'delete'."}), 400

    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to process pet update/delete"}), 500


@app.route('/user/login', methods=['POST'])
async def user_login():
    """
    Logs in the user by authenticating with the external Petstore API.
    Note: The external API endpoint for login is GET, but we are invoking it from our POST endpoint.
    """
    try:
        credentials = await request.get_json()
        username = credentials.get("username")
        password = credentials.get("password")
        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400

        params = {"username": username, "password": password}
        async with httpx.AsyncClient() as client:
            # External API expects GET, so we use GET here with query parameters.
            response = await client.get(
                "https://petstore.swagger.io/v2/user/login",
                params=params,
                timeout=10.0
            )
            response.raise_for_status()
            # The external API returns a string message; here we wrap it in JSON format.
            message = response.text
        return jsonify({"token": message})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "User login failed"}), 500


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)