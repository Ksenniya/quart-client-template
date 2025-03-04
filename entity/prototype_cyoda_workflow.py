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

# Data classes for request validation (using only primitives)
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

# Workflow functions: they are applied asynchronously to the entity before it is persisted.
# They take the entity dict as the only argument and can modify it directly.

async def process_pet(pet: dict):
    """
    Enrich the pet entity by calling an external API.
    The external data is added to pet['externalData'].
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("https://petstore.swagger.io/v2/pet", json=pet)
            response.raise_for_status()
            external_info = response.json()  # Real external data response.
    except Exception as e:
        logger.exception(e)
        external_info = {"info": "external service unavailable"}  # Fallback response.
    pet["externalData"] = external_info
    return pet

async def process_order(order: dict):
    """
    Enrich the order entity by calling an external API.
    The calculation result is added to order['externalCalculation'].
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("https://petstore.swagger.io/v2/store/order", json=order)
            response.raise_for_status()
            calculation_data = response.json()  # Real calculation/order result.
    except Exception as e:
        logger.exception(e)
        calculation_data = {"calculation": "default value"}  # Fallback data.
    order["externalCalculation"] = calculation_data
    return order

async def process_user(user: dict):
    """
    Process the user entity by calling an external authentication API.
    The authentication result is added to user['authResult'].
    Note: This workflow function is only applied when creating a new user.
    When logging in an existing user, it can be invoked separately on a copy.
    """
    try:
        async with httpx.AsyncClient() as client:
            params = {"username": user.get("username"), "password": user.get("password")}
            response = await client.get("https://petstore.swagger.io/v2/user/login", params=params)
            response.raise_for_status()
            auth_result = response.json()  # Real authentication response.
    except Exception as e:
        logger.exception(e)
        auth_result = {"authenticated": True}  # Fallback dummy authentication.
    user["authResult"] = auth_result
    return user

@app.route('/api/pet', methods=['POST'])
@validate_request(PetData)  # For POST endpoints, put this after the route decorator.
async def create_pet(data: PetData):
    pet = data.__dict__.copy()
    try:
        pet_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=pet,
            workflow=process_pet  # Run asynchronous pet enrichment before persistence.
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
@validate_request(OrderData)  # For POST endpoints, put this after the route decorator.
async def place_order(data: OrderData):
    order = data.__dict__.copy()
    try:
        order_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="order",
            entity_version=ENTITY_VERSION,
            entity=order,
            workflow=process_order  # Run asynchronous order enrichment before persistence.
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
@validate_request(UserLoginData)  # For POST endpoints, put this after the route decorator.
async def user_login(data: UserLoginData):
    credentials = data.__dict__.copy()
    username = credentials.get("username")
    password = credentials.get("password")
    if not username or not password:
        abort(400, description="Username and password are required")
    try:
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
        # Create a basic user with password included for authentication in workflow.
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
            # Persist the new user with asynchronous processing via workflow.
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
        # For an existing user, invoke the workflow function on a copy to get latest auth data.
        # (Do not persist an update on the current user to avoid recursion.)
        user = await process_user(user.copy())
    if not user.get("authResult", {}).get("authenticated", False):
        abort(401, description="Authentication failed")
    token_str = f"dummy-token-{username}"  # TODO: Replace with secure token generation.
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