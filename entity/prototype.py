import asyncio
import httpx
import logging
import time
import uuid
from dataclasses import dataclass

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

app = Quart(__name__)
QuartSchema(app)  # initialize QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# In-memory caches (mock persistence)
pets_cache = {}      # {pet_id: pet_data}
orders_cache = {}    # {order_id: order_data}
users_cache = {}     # {user_id: user_data}
entity_jobs = {}     # {job_id: job_status}

# Data classes for request validation
# Using only primitives per quart-schema guidelines.
@dataclass
class PetData:
    id: str  # Expect client to send string id; if not provided, a uuid will be used.
    name: str
    photoUrls: str  # Comma separated URLs
    status: str

@dataclass
class PetStatusRequest:
    # Workaround: Instead of list, we use a comma separated string.
    status: str

@dataclass
class OrderData:
    id: str
    petId: str
    quantity: int
    shipDate: str
    status: str
    complete: bool

@dataclass
class UserData:
    id: str
    username: str
    firstName: str
    lastName: str
    email: str
    password: str
    phone: str
    userStatus: int

# Asynchronous background process for entity work
async def process_entity(job, entity_data: dict):
    try:
        # TODO: Replace this with real processing logic if needed.
        await asyncio.sleep(2)  # simulate processing delay
        # Modify entity_data as required during processing.
        job["status"] = "completed"
        job["completedAt"] = time.time()
        logger.info(f"Processed entity data: {entity_data}")
    except Exception as e:
        logger.exception(e)
        job["status"] = "failed"

# Endpoint: Add a new pet
@app.route('/pet', methods=['POST'])
@validate_request(PetData)  # For POST, validation is placed after the route decorator.
async def add_pet(data: PetData):
    try:
        # Convert dataclass to dict
        pet_dict = data.__dict__
        job_id = str(uuid.uuid4())
        # Mark the job as processing
        entity_jobs[job_id] = {"status": "processing", "requestedAt": time.time()}
        # Fire-and-forget processing task
        asyncio.create_task(process_entity(entity_jobs[job_id], pet_dict))
        # Use provided ID or generate one if missing
        pet_id = pet_dict.get("id") or str(uuid.uuid4())
        pets_cache[pet_id] = pet_dict
        logger.info(f"Added pet with id: {pet_id}")
        return jsonify({"job_id": job_id, "message": "Pet submission received and processing started"}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add pet"}), 500

# Endpoint: Find pets by status using external API
@app.route('/pet/findByStatus', methods=['POST'])
@validate_request(PetStatusRequest)
async def find_pet_by_status(data: PetStatusRequest):
    try:
        # data.status is expected as a comma separated string.
        status_list = data.status.split(',')
        params = {'status': ','.join([s.strip() for s in status_list])}
        async with httpx.AsyncClient() as client:
            # The external API requires a GET request; we invoke it within our POST endpoint.
            response = await client.get("https://petstore.swagger.io/v2/pet/findByStatus", params=params)
            response.raise_for_status()
            pets = response.json()
        logger.info("Retrieved pets from external API by status")
        return jsonify(pets), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pets by status"}), 500

# Endpoint: Place an order for a pet
@app.route('/store/order', methods=['POST'])
@validate_request(OrderData)
async def place_order(data: OrderData):
    try:
        order_dict = data.__dict__
        order_id = order_dict.get("id") or str(uuid.uuid4())
        orders_cache[order_id] = order_dict
        logger.info(f"Order placed with id: {order_id}")
        return jsonify(order_dict), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to place order"}), 500

# Endpoint: Create a new user
@app.route('/user', methods=['POST'])
@validate_request(UserData)
async def create_user(data: UserData):
    try:
        user_dict = data.__dict__
        user_id = user_dict.get("id") or str(uuid.uuid4())
        users_cache[user_id] = user_dict
        logger.info(f"User created with id: {user_id}")
        # Return a subset of user info in the response
        user_response = {
            "id": user_dict.get("id"),
            "username": user_dict.get("username"),
            "firstName": user_dict.get("firstName"),
            "lastName": user_dict.get("lastName"),
            "email": user_dict.get("email")
        }
        return jsonify(user_response), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to create user"}), 500

# Additional endpoint: Retrieve job status (GET request does not require validation)
# For GET requests with query parameters, validation should appear before the route decorator.
@app.route('/job/<job_id>', methods=['GET'])
async def get_job_status(job_id):
    try:
        job = entity_jobs.get(job_id)
        if job is None:
            return jsonify({"error": "Job not found"}), 404
        return jsonify(job), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve job status"}), 500

# Note: Due to an issue with quart-schema, for GET requests with query parameters,
# the @validate_querystring decorator must be positioned first (before @app.route).
# However, since our GET endpoint here does not require request parameters, no validation is added.

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)