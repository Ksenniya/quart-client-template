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

# Removed local in‐memory caches: pets_cache, orders_cache, users_cache
# Retaining entity_jobs for the job status endpoint (even though no new jobs are created)
entity_jobs = {}     # {job_id: job_status}

# Supplementary async tasks for fire and forget processing

async def send_pet_notification(entity):
    # Simulate sending a notification for the pet entity
    await asyncio.sleep(0)
    # For example, add supplementary data or notify another service
    return

async def send_order_notification(entity):
    # Simulate sending a notification for the order entity
    await asyncio.sleep(0)
    return

async def send_welcome_email(entity):
    # Simulate sending a welcome email for the user entity
    await asyncio.sleep(0)
    return

# Workflow functions applied to entities before persistence

async def process_pet(entity):
    # Modify the pet entity state
    entity["processed"] = True
    entity["processed_timestamp"] = time.time()
    # Fire and forget any async tasks such as sending notifications
    asyncio.create_task(send_pet_notification(entity))
    return entity

async def process_order(entity):
    # Modify the order entity state
    entity["validated"] = True
    entity["order_processed_timestamp"] = time.time()
    # Fire and forget sending order notification
    asyncio.create_task(send_order_notification(entity))
    return entity

async def process_user(entity):
    # Update sensitive information, e.g., hash the password
    entity["password"] = "hashed_" + entity["password"]
    # Fire and forget sending welcome email (do not modify entity state in fire and forget tasks)
    asyncio.create_task(send_welcome_email(entity))
    return entity

# Data classes for request validation
@dataclass
class PetData:
    id: str  # Expect client to send string id; if not provided, a uuid will be used.
    name: str
    photoUrls: str  # Comma separated URLs
    status: str

@dataclass
class PetStatusRequest:
    # Instead of list, we use a comma separated string.
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
@validate_request(PetData)
async def add_pet(data: PetData):
    try:
        pet_dict = data.__dict__
        # Persist the pet after applying asynchronous workflow processing
        pet_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="pet",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=pet_dict,  # the validated data object
            workflow=process_pet  # Workflow function applied to the entity before persistence
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
        status_list = [s.strip() for s in data.status.split(',')]
        params = {'status': ','.join(status_list)}
        async with httpx.AsyncClient() as client:
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
        # Persist the order after applying async workflow processing
        order_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="order",
            entity_version=ENTITY_VERSION,
            entity=order_dict,
            workflow=process_order  # Workflow function applied to the order entity
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
        # Persist the user after applying async workflow processing
        user_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="user",
            entity_version=ENTITY_VERSION,
            entity=user_dict,
            workflow=process_user  # Workflow function applied to the user entity
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