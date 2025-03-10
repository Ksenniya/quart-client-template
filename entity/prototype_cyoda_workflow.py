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

# Workflow function for pets entity
async def process_pets(entity):
    try:
        # Simulate asynchronous processing delay if required
        await asyncio.sleep(2)  # Simulated delay for processing
        # Add additional processing on pet data if needed
        if isinstance(entity, list):
            for item in entity:
                # Modify each pet item with a processing timestamp and additional flag
                item["processed_at"] = datetime.datetime.utcnow().isoformat()
                item["pre_persist_validated"] = True
        elif isinstance(entity, dict):
            entity["processed_at"] = datetime.datetime.utcnow().isoformat()
            entity["pre_persist_validated"] = True
        logger.info("Pets workflow processing complete")
    except Exception as wf_error:
        logger.exception("Error in process_pets: %s", wf_error)
        # Optionally modify entity to signal error state if applicable
    return entity

# Workflow function for orders entity
async def process_orders(entity):
    try:
        # Simulate asynchronous processing delay if required
        await asyncio.sleep(2)  # Simulated delay for processing
        # Add additional processing on orders data if needed
        if isinstance(entity, list):
            for item in entity:
                item["processed_at"] = datetime.datetime.utcnow().isoformat()
                item["order_validated"] = True
        elif isinstance(entity, dict):
            entity["processed_at"] = datetime.datetime.utcnow().isoformat()
            entity["order_validated"] = True
        logger.info("Orders workflow processing complete")
    except Exception as wf_error:
        logger.exception("Error in process_orders: %s", wf_error)
    return entity

# Workflow function for users entity
async def process_users(entity):
    try:
        # Simulate asynchronous processing delay if required
        await asyncio.sleep(2)  # Simulated delay for processing
        # Add additional processing on users data if needed
        if isinstance(entity, list):
            for item in entity:
                item["verified_at"] = datetime.datetime.utcnow().isoformat()
                item["user_validated"] = True
        elif isinstance(entity, dict):
            entity["verified_at"] = datetime.datetime.utcnow().isoformat()
            entity["user_validated"] = True
        logger.info("Users workflow processing complete")
    except Exception as wf_error:
        logger.exception("Error in process_users: %s", wf_error)
    return entity

# Endpoint for fetching and storing pet data
@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)
async def fetch_pets(data: FetchPetsRequest):
    """
    Fetch pet data from the external Petstore API based on status and optional filters.
    The asynchronous processing logic is moved to the workflow function process_pets.
    """
    status = data.status or "available"
    filters = data.filters or {}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://petstore.swagger.io/v2/pet/findByStatus",
                params={"status": status}
            )
            response.raise_for_status()
            pets = response.json()
        except Exception as e:
            logger.exception("Error fetching pets: %s", e)
            return jsonify({"message": "Failed to fetch pets"}), 500

    try:
        # The workflow function (process_pets) applies all asynchronous pre-processing logic
        item_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="pets",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=pets,
            workflow=process_pets  # workflow function invoked asynchronously before persistence
        )
    except Exception as e:
        logger.exception("Error storing pets: %s", e)
        return jsonify({"message": "Failed to store pet data"}), 500

    logger.info("Pets fetched and stored under %s with status %s", item_id, status)
    return jsonify({"message": "Data fetched and processed", "job_id": item_id})

# Endpoint for fetching and storing orders data
@app.route("/orders/fetch", methods=["POST"])
@validate_request(FetchOrdersRequest)
async def fetch_orders(data: FetchOrdersRequest):
    """
    Fetch order data from the external Petstore API.
    The asynchronous processing logic is moved to the workflow function process_orders.
    """
    orderCriteria = data.orderCriteria or "recent"
    orderId = data.orderId

    async with httpx.AsyncClient() as client:
        try:
            if orderCriteria == "byId" and orderId:
                response = await client.get(f"https://petstore.swagger.io/v2/store/order/{orderId}")
            else:
                # Fallback: using inventory data as an example for recent orders.
                response = await client.get("https://petstore.swagger.io/v2/store/inventory")
            response.raise_for_status()
            orders = response.json()
        except Exception as e:
            logger.exception("Error fetching orders: %s", e)
            return jsonify({"message": "Failed to fetch orders"}), 500

    try:
        # The workflow function (process_orders) applies all asynchronous pre-processing logic
        item_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="orders",
            entity_version=ENTITY_VERSION,
            entity=orders,
            workflow=process_orders
        )
    except Exception as e:
        logger.exception("Error storing orders: %s", e)
        return jsonify({"message": "Failed to store order data"}), 500

    logger.info("Orders fetched and stored under %s", item_id)
    return jsonify({"message": "Orders data fetched and processed", "job_id": item_id})

# Endpoint for fetching and storing user data
@app.route("/users/fetch", methods=["POST"])
@validate_request(FetchUsersRequest)
async def fetch_users(data: FetchUsersRequest):
    """
    Fetch user data from the external Petstore API by username.
    The asynchronous processing logic is moved to the workflow function process_users.
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
            logger.exception("Error fetching user: %s", e)
            return jsonify({"message": "Failed to fetch user"}), 500

    try:
        # The workflow function (process_users) applies all asynchronous pre-processing logic
        item_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="users",
            entity_version=ENTITY_VERSION,
            entity=user,
            workflow=process_users
        )
    except Exception as e:
        logger.exception("Error storing user: %s", e)
        return jsonify({"message": "Failed to store user data"}), 500

    logger.info("User %s fetched and stored under %s", username, item_id)
    return jsonify({"message": "User data fetched and processed", "job_id": item_id})

# Endpoint for retrieving pet data
@validate_querystring(QueryJobRequest)
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
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model="pets",
            entity_version=ENTITY_VERSION
        )
        return jsonify(data)
    except Exception as e:
        logger.exception("Error retrieving pets: %s", e)
        return jsonify({"message": "Error retrieving pet data"}), 500

# Endpoint for retrieving order data
@validate_querystring(QueryJobRequest)
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
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model="orders",
            entity_version=ENTITY_VERSION
        )
        return jsonify(data)
    except Exception as e:
        logger.exception("Error retrieving orders: %s", e)
        return jsonify({"message": "Error retrieving order data"}), 500

# Endpoint for retrieving user data
@validate_querystring(QueryJobRequest)
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
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model="users",
            entity_version=ENTITY_VERSION
        )
        return jsonify(data)
    except Exception as e:
        logger.exception("Error retrieving users: %s", e)
        return jsonify({"message": "Error retrieving user data"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)