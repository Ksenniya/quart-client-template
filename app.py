from common.grpc_client.grpc_client import grpc_stream
import asyncio
import httpx
import logging
import time
from dataclasses import dataclass

from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)  # initialize QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# This dict is used for tracking asynchronous job statuses (if needed)
entity_jobs = {}  # {job_id: job_status}

# Data classes for request validation
# Using only primitive types per quart-schema guidelines

@dataclass
class PetData:
    id: str  # if not provided, a uuid should be generated at client side or within business logic
    name: str
    photoUrls: str  # Comma separated URLs
    status: str

@dataclass
class PetStatusRequest:
    # Instead of a list, we use a comma separated string
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

# Startup hook for initializing external systems, such as cyoda
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task
        logger.info("Cyoda initialization complete")
    except Exception as e:
        logger.exception(f"Error during startup initialization: {e}")

# Endpoint: Add a new pet
@app.route('/pet', methods=['POST'])
@validate_request(PetData)
async def add_pet(data: PetData):
    try:
        pet_dict = data.__dict__
        # Persist the pet after applying asynchronous workflow processing (process_pet)
        pet_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="pet",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=pet_dict,  # the validated data object
            )
        logger.info(f"Added pet with id: {pet_id}")
        return jsonify({"id": pet_id, "message": "Pet submission received"}), 200
    except Exception as e:
        logger.exception(f"Error adding pet: {e}")
        return jsonify({"error": "Failed to add pet"}), 500

# Endpoint: Find pets by status using external API
@app.route('/pet/findByStatus', methods=['POST'])
@validate_request(PetStatusRequest)
async def find_pet_by_status(data: PetStatusRequest):
    try:
        # data.status is provided as a comma separated string
        status_list = [status.strip() for status in data.status.split(',')]
        params = {'status': ','.join(status_list)}
        async with httpx.AsyncClient() as client:
            response = await client.get("https://petstore.swagger.io/v2/pet/findByStatus", params=params)
            response.raise_for_status()
            pets = response.json()
        logger.info("Retrieved pets from external API by status")
        return jsonify(pets), 200
    except Exception as e:
        logger.exception(f"Error retrieving pets by status: {e}")
        return jsonify({"error": "Failed to retrieve pets by status"}), 500

# Endpoint: Place an order for a pet
@app.route('/store/order', methods=['POST'])
@validate_request(OrderData)
async def place_order(data: OrderData):
    try:
        order_dict = data.__dict__
        # Persist the order after applying asynchronous workflow processing (process_order)
        order_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="order",
            entity_version=ENTITY_VERSION,
            entity=order_dict,
            )
        logger.info(f"Order placed with id: {order_id}")
        return jsonify({"id": order_id}), 200
    except Exception as e:
        logger.exception(f"Error placing order: {e}")
        return jsonify({"error": "Failed to place order"}), 500

# Endpoint: Create a new user
@app.route('/user', methods=['POST'])
@validate_request(UserData)
async def create_user(data: UserData):
    try:
        user_dict = data.__dict__
        # Persist the user after applying asynchronous workflow processing (process_user)
        user_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="user",
            entity_version=ENTITY_VERSION,
            entity=user_dict,
            )
        logger.info(f"User created with id: {user_id}")
        return jsonify({"id": user_id, "message": "User created"}), 200
    except Exception as e:
        logger.exception(f"Error creating user: {e}")
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
        logger.exception(f"Error retrieving job status for job id {job_id}: {e}")
        return jsonify({"error": "Failed to retrieve job status"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)