import asyncio
import httpx
import logging
import time
import uuid
from dataclasses import dataclass

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)  # initialize QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Removed local in‐memory caches: pets_cache, orders_cache, users_cache
# Retaining entity_jobs for the job status endpoint (even though no new jobs are created)
entity_jobs = {}     # {job_id: job_status}

# Workflow functions applied to entities before persistence
async def process_pet(entity):
    # Example: mark the pet as processed, you can modify other attributes as needed
    entity["processed"] = True
    await asyncio.sleep(0)  # simulate asynchronous processing
    return entity

async def process_order(entity):
    # Example: add a validated flag to the order
    entity["validated"] = True
    await asyncio.sleep(0)
    return entity

async def process_user(entity):
    # Example: hash the password and update the user entity
    entity["password"] = "hashed_" + entity["password"]
    await asyncio.sleep(0)
    return entity

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

# Startup initialization of cyoda
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Endpoint: Add a new pet
@app.route('/pet', methods=['POST'])
@validate_request(PetData)  # For POST, validation is placed after the route decorator.
async def add_pet(data: PetData):
    try:
        pet_dict = data.__dict__
        # Call external entity_service to add the pet with workflow function process_pet
        pet_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="pet",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=pet_dict,  # the validated data object
            workflow=process_pet  # Workflow function applied to the entity asynchronously before persistence
        )
        logger.info(f"Added pet with id: {pet_id}")
        return jsonify({"id": pet_id, "message": "Pet submission received"}), 200
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
        order_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="order",
            entity_version=ENTITY_VERSION,
            entity=order_dict,
            workflow=process_order  # Workflow function applied to the order
        )
        logger.info(f"Order placed with id: {order_id}")
        return jsonify({"id": order_id}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to place order"}), 500

# Endpoint: Create a new user
@app.route('/user', methods=['POST'])
@validate_request(UserData)
async def create_user(data: UserData):
    try:
        user_dict = data.__dict__
        user_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="user",
            entity_version=ENTITY_VERSION,
            entity=user_dict,
            workflow=process_user  # Workflow function applied to the user
        )
        logger.info(f"User created with id: {user_id}")
        return jsonify({"id": user_id, "message": "User created"}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to create user"}), 500

# Additional endpoint: Retrieve job status
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

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)