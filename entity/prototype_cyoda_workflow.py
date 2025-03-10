#!/usr/bin/env python
import asyncio
import datetime
import logging
from dataclasses import dataclass
from typing import Optional, Any

from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring
import httpx

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Request models
@dataclass
class FetchPetsRequest:
    status: str
    filters: Optional[Any] = None  # TODO: Define filters schema properly

@dataclass
class FetchOrdersRequest:
    orderCriteria: str
    orderId: Optional[int] = None

@dataclass
class FetchUsersRequest:
    username: str

@dataclass
class QueryJobRequest:
    job_id: Optional[str] = None

# Dummy processing function to simulate background work.
async def process_entity(entity_type, job_id, data):
    # TODO: Implement specific processing logic and calculations as required.
    await asyncio.sleep(2)  # Simulate processing delay
    logger.info(f"Processing complete for {entity_type} with job_id {job_id}")

# Workflow function for pets entity
async def process_pets(entity):
    # Example: add a processed timestamp to the pet data
    if isinstance(entity, list):
        for item in entity:
            item["processed_at"] = datetime.datetime.utcnow().isoformat()
    elif isinstance(entity, dict):
        entity["processed_at"] = datetime.datetime.utcnow().isoformat()
    return entity

# Workflow function for orders entity
async def process_orders(entity):
    # Example: add a processed flag to orders data
    if isinstance(entity, list):
        for item in entity:
            item["processed"] = True
    elif isinstance(entity, dict):
        entity["processed"] = True
    return entity

# Workflow function for users entity
async def process_users(entity):
    # Example: add a verification timestamp to user data
    if isinstance(entity, list):
        for item in entity:
            item["verified_at"] = datetime.datetime.utcnow().isoformat()
    elif isinstance(entity, dict):
        entity["verified_at"] = datetime.datetime.utcnow().isoformat()
    return entity

# Workaround: For POST endpoints, route decorator must come first then validate_request.
@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)
async def fetch_pets(data: FetchPetsRequest):
    """
    Fetch pet data from the external Petstore API based on status and optional filters.
    """
    status = data.status or "available"
    filters = data.filters or {}
    # TODO: Implement detailed filtering logic based on received filters.
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://petstore.swagger.io/v2/pet/findByStatus",
                params={"status": status}
            )
            response.raise_for_status()
            pets = response.json()
        except Exception as e:
            logger.exception(e)
            return jsonify({"message": "Failed to fetch pets"}), 500

    try:
        item_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="pets",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=pets,
            workflow=process_pets  # workflow function applied before persistence
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Failed to store pet data"}), 500

    logger.info(f"Pets fetched and stored under {item_id} with status {status}")
    asyncio.create_task(process_entity("pets", item_id, pets))
    return jsonify({"message": "Data fetched and processing started", "job_id": item_id})

# Workaround: For POST endpoints, route decorator must come first then validate_request.
@app.route("/orders/fetch", methods=["POST"])
@validate_request(FetchOrdersRequest)
async def fetch_orders(data: FetchOrdersRequest):
    """
    Fetch order data from the external Petstore API.
    When orderCriteria is 'byId', a specific order is fetched, otherwise, a fallback action is taken.
    """
    orderCriteria = data.orderCriteria or "recent"
    orderId = data.orderId

    async with httpx.AsyncClient() as client:
        try:
            if orderCriteria == "byId" and orderId:
                response = await client.get(f"https://petstore.swagger.io/v2/store/order/{orderId}")
            else:
                # TODO: Identify a proper API call for 'recent' orders if available.
                response = await client.get("https://petstore.swagger.io/v2/store/inventory")
            response.raise_for_status()
            orders = response.json()
        except Exception as e:
            logger.exception(e)
            return jsonify({"message": "Failed to fetch orders"}), 500

    try:
        item_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="orders",
            entity_version=ENTITY_VERSION,
            entity=orders,
            workflow=process_orders  # workflow function applied before persistence
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Failed to store order data"}), 500

    logger.info(f"Orders fetched and stored under {item_id}")
    asyncio.create_task(process_entity("orders", item_id, orders))
    return jsonify({"message": "Orders data fetched and processing started", "job_id": item_id})

# Workaround: For POST endpoints, route decorator must come first then validate_request.
@app.route("/users/fetch", methods=["POST"])
@validate_request(FetchUsersRequest)
async def fetch_users(data: FetchUsersRequest):
    """
    Fetch user data from the external Petstore API by username.
    """
    username = data.username
    if not username:
        return jsonify({"message": "username is required"}), 400

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"https://petstore.swagger.io/v2/user/{username}")
            response.raise_for_status()
            user = response.json()
        except Exception as e:
            logger.exception(e)
            return jsonify({"message": "Failed to fetch user"}), 500

    try:
        item_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="users",
            entity_version=ENTITY_VERSION,
            entity=user,
            workflow=process_users  # workflow function applied before persistence
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Failed to store user data"}), 500

    logger.info(f"User {username} fetched and stored under {item_id}")
    asyncio.create_task(process_entity("users", item_id, user))
    return jsonify({"message": "User data fetched and processing started", "job_id": item_id})

# Workaround: For GET endpoints, validation decorator must come first.
@validate_querystring(QueryJobRequest)  # Workaround for GET: validation decorator placed first.
@app.route("/pets", methods=["GET"])
async def get_pets():
    """
    Retrieve stored pet data. Optionally filter by job_id.
    """
    job_id = request.args.get("job_id")
    try:
        if job_id:
            data = await entity_service.get_item(
                token=cyoda_token,
                entity_model="pets",
                entity_version=ENTITY_VERSION,
                technical_id=job_id
            )
            if not data:
                return jsonify({"message": "No data found for the provided job_id"}), 404
            return jsonify(data)
        else:
            data = await entity_service.get_items(
                token=cyoda_token,
                entity_model="pets",
                entity_version=ENTITY_VERSION
            )
            return jsonify(data)
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Error retrieving pet data"}), 500

# Workaround: For GET endpoints, validation decorator must come first.
@validate_querystring(QueryJobRequest)  # Workaround for GET: validation decorator placed first.
@app.route("/orders", methods=["GET"])
async def get_orders():
    """
    Retrieve stored order data. Optionally filter by job_id.
    """
    job_id = request.args.get("job_id")
    try:
        if job_id:
            data = await entity_service.get_item(
                token=cyoda_token,
                entity_model="orders",
                entity_version=ENTITY_VERSION,
                technical_id=job_id
            )
            if not data:
                return jsonify({"message": "No data found for the provided job_id"}), 404
            return jsonify(data)
        else:
            data = await entity_service.get_items(
                token=cyoda_token,
                entity_model="orders",
                entity_version=ENTITY_VERSION
            )
            return jsonify(data)
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Error retrieving order data"}), 500

# Workaround: For GET endpoints, validation decorator must come first.
@validate_querystring(QueryJobRequest)  # Workaround for GET: validation decorator placed first.
@app.route("/users", methods=["GET"])
async def get_users():
    """
    Retrieve stored user data. Optionally filter by job_id.
    """
    job_id = request.args.get("job_id")
    try:
        if job_id:
            data = await entity_service.get_item(
                token=cyoda_token,
                entity_model="users",
                entity_version=ENTITY_VERSION,
                technical_id=job_id
            )
            if not data:
                return jsonify({"message": "No data found for the provided job_id"}), 404
            return jsonify(data)
        else:
            data = await entity_service.get_items(
                token=cyoda_token,
                entity_model="users",
                entity_version=ENTITY_VERSION
            )
            return jsonify(data)
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Error retrieving user data"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)