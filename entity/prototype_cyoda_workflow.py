#!/usr/bin/env python3
import asyncio
import logging
import datetime
import uuid

import httpx
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request  # For POST endpoints
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Data classes for request validation
from dataclasses import dataclass

@dataclass
class PetData:
    name: str
    category: str
    photoUrls: list  # TODO: Ensure list contains only strings if needed.
    tags: list       # TODO: Ensure list contains only strings if needed.
    status: str

@dataclass
class OrderData:
    petId: int
    quantity: int
    shipDate: str
    status: str
    complete: bool

@dataclass
class UserLoginData:
    username: str
    password: str

# Workflow functions: They are applied asynchronously to the entity before persistence.
# They receive the entity dict as the only argument and modify it directly.
# Do not call entity_service.add/update/delete on current entity to avoid recursion.

async def process_pet(pet: dict):
    """
    Enrich the pet entity by calling an external API.
    The result is stored directly in pet['externalData'].
    """
    try:
        async with httpx.AsyncClient() as client:
            # Call external API with the pet data
            response = await client.post("https://petstore.swagger.io/v2/pet", json=pet)
            response.raise_for_status()
            external_info = response.json()
    except Exception as e:
        logger.exception(e)
        external_info = {"info": "external service unavailable"}
    pet["externalData"] = external_info
    # Additional transformation example: mark pet as "processed"
    pet["processedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    return pet

async def process_order(order: dict):
    """
    Enrich the order entity by calling an external API.
    The calculation result is stored in order['externalCalculation'].
    """
    try:
        async with httpx.AsyncClient() as client:
            # Post the order data to the external service
            response = await client.post("https://petstore.swagger.io/v2/store/order", json=order)
            response.raise_for_status()
            calculation_data = response.json()
    except Exception as e:
        logger.exception(e)
        calculation_data = {"calculation": "default value"}
    order["externalCalculation"] = calculation_data
    # Additional transformation: add a timestamp for order processing
    order["processedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    return order

async def process_user(user: dict):
    """
    Enrich the user entity by calling an external authentication API.
    The authentication result is stored in user['authResult'].
    This function is used only during user creation.
    """
    # Ensure that username and password exist to call external auth.
    username = user.get("username")
    password = user.get("password")
    if username and password:
        try:
            async with httpx.AsyncClient() as client:
                params = {"username": username, "password": password}
                response = await client.get("https://petstore.swagger.io/v2/user/login", params=params)
                response.raise_for_status()
                auth_result = response.json()
        except Exception as e:
            logger.exception(e)
            auth_result = {"authenticated": True}  # Fallback dummy authentication
        user["authResult"] = auth_result
    else:
        user["authResult"] = {"authenticated": False}
    # Remove password from the entity before persistence for security reasons.
    if "password" in user:
        del user["password"]
    user["createdAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    return user

@app.route('/api/pet', methods=['POST'])
@validate_request(PetData)
async def create_pet(data: PetData):
    pet = data.__dict__.copy()
    try:
        # The workflow function process_pet is called before persistence.
        pet_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=pet,
            workflow=process_pet
        )
        logger.info(f"Created pet with ID {pet_id}")
        return jsonify({"id": pet_id}), 201
    except Exception as e:
        logger.exception(e)
        abort(500, description="Failed to create pet")

@app.route('/api/pet/<int:pet_id>', methods=['GET'])
async def retrieve_pet(pet_id: int):
    try:
        pet = await entity_service.get_item(
            token=cyoda_token,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
        if not pet:
            abort(404, description="Pet not found")
        return jsonify(pet)
    except Exception as e:
        logger.exception(e)
        abort(500, description="Failed to retrieve pet")

@app.route('/api/order', methods=['POST'])
@validate_request(OrderData)
async def place_order(data: OrderData):
    order = data.__dict__.copy()
    try:
        # The workflow function process_order is applied before the order is persisted.
        order_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="order",
            entity_version=ENTITY_VERSION,
            entity=order,
            workflow=process_order
        )
        logger.info(f"Placed order with ID {order_id}")
        return jsonify({"id": order_id}), 201
    except Exception as e:
        logger.exception(e)
        abort(500, description="Failed to place order")

@app.route('/api/order/<int:order_id>', methods=['GET'])
async def retrieve_order(order_id: int):
    try:
        order = await entity_service.get_item(
            token=cyoda_token,
            entity_model="order",
            entity_version=ENTITY_VERSION,
            technical_id=order_id
        )
        if not order:
            abort(404, description="Order not found")
        return jsonify(order)
    except Exception as e:
        logger.exception(e)
        abort(500, description="Failed to retrieve order")

@app.route('/api/user/login', methods=['POST'])
@validate_request(UserLoginData)
async def user_login(data: UserLoginData):
    credentials = data.__dict__.copy()
    username = credentials.get("username")
    password = credentials.get("password")
    if not username or not password:
        abort(400, description="Username and password are required")
    try:
        # Attempt to get existing user
        user = await entity_service.get_item(
            token=cyoda_token,
            entity_model="user",
            entity_version=ENTITY_VERSION,
            technical_id=username
        )
    except Exception as e:
        logger.exception(e)
        user = None
    if not user:
        # Create new user with credentials; include password for authentication in workflow.
        basic_user = {
            "id": str(uuid.uuid4()),
            "username": username,
            "password": password,
            "firstName": "TODO",         # TODO: Replace with actual details if available.
            "lastName": "TODO",          # TODO: Replace with actual details if available.
            "email": "TODO@example.com", # TODO: Replace with actual details if available.
            "phone": "TODO",             # TODO: Replace with actual details if available.
            "userStatus": 1
        }
        try:
            # Persist user with asynchronous processing via workflow.
            user = await entity_service.add_item(
                token=cyoda_token,
                entity_model="user",
                entity_version=ENTITY_VERSION,
                entity=basic_user,
                workflow=process_user
            )
        except Exception as e:
            logger.exception(e)
            abort(500, description="Failed to create user")
    else:
        # For an existing user, get updated auth info by processing a copy
        updated_user = await process_user(user.copy())
        user["authResult"] = updated_user.get("authResult", {})
    # Validate authentication result from the workflow.
    if not user.get("authResult", {}).get("authenticated", False):
        abort(401, description="Authentication failed")
    token_str = f"dummy-token-{username}"  # Replace with secure token generation in production.
    expires_at = (datetime.datetime.utcnow() + datetime.timedelta(hours=1)).isoformat() + "Z"
    result = {"username": username, "token": token_str, "expiresAt": expires_at}
    logger.info(f"User {username} logged in successfully.")
    return jsonify(result)

@app.route('/api/user/<string:username>', methods=['GET'])
async def retrieve_user(username: str):
    try:
        user = await entity_service.get_item(
            token=cyoda_token,
            entity_model="user",
            entity_version=ENTITY_VERSION,
            technical_id=username
        )
        if not user:
            abort(404, description="User not found")
        return jsonify(user)
    except Exception as e:
        logger.exception(e)
        abort(500, description="Failed to retrieve user")

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)