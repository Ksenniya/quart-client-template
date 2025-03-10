import asyncio
import datetime
import logging
from dataclasses import dataclass
from typing import Optional, Any

from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring
import httpx

app = Quart(__name__)
QuartSchema(app)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# In-memory caches for persistence (mocked)
pets_cache = {}
orders_cache = {}
users_cache = {}

job_counter = 1

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

    global job_counter
    job_id = f"job_{job_counter}"
    job_counter += 1
    pets_cache[job_id] = pets
    logger.info(f"Pets fetched and stored under {job_id} with status {status}")

    # Fire and forget the processing task.
    asyncio.create_task(process_entity("pets", job_id, pets))
    return jsonify({"message": "Data fetched and processing started", "job_id": job_id})

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

    global job_counter
    job_id = f"job_{job_counter}"
    job_counter += 1
    orders_cache[job_id] = orders
    logger.info(f"Orders fetched and stored under job_id {job_id}")

    asyncio.create_task(process_entity("orders", job_id, orders))
    return jsonify({"message": "Orders data fetched and processing started", "job_id": job_id})

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

    global job_counter
    job_id = f"job_{job_counter}"
    job_counter += 1
    users_cache[job_id] = user
    logger.info(f"User {username} fetched and stored under job_id {job_id}")

    asyncio.create_task(process_entity("users", job_id, user))
    return jsonify({"message": "User data fetched and processing started", "job_id": job_id})

# Workaround: For GET endpoints, validation decorator must come first.
@validate_querystring(QueryJobRequest)  # Workaround for GET: validation decorator placed first.
@app.route("/pets", methods=["GET"])
async def get_pets():
    """
    Retrieve stored pet data. Optionally filter by job_id.
    """
    job_id = request.args.get("job_id")
    if job_id:
        data = pets_cache.get(job_id)
        if not data:
            return jsonify({"message": "No data found for the provided job_id"}), 404
        return jsonify(data)
    else:
        return jsonify(list(pets_cache.values()))

# Workaround: For GET endpoints, validation decorator must come first.
@validate_querystring(QueryJobRequest)  # Workaround for GET: validation decorator placed first.
@app.route("/orders", methods=["GET"])
async def get_orders():
    """
    Retrieve stored order data. Optionally filter by job_id.
    """
    job_id = request.args.get("job_id")
    if job_id:
        data = orders_cache.get(job_id)
        if not data:
            return jsonify({"message": "No data found for the provided job_id"}), 404
        return jsonify(data)
    else:
        return jsonify(list(orders_cache.values()))

# Workaround: For GET endpoints, validation decorator must come first.
@validate_querystring(QueryJobRequest)  # Workaround for GET: validation decorator placed first.
@app.route("/users", methods=["GET"])
async def get_users():
    """
    Retrieve stored user data. Optionally filter by job_id.
    """
    job_id = request.args.get("job_id")
    if job_id:
        data = users_cache.get(job_id)
        if not data:
            return jsonify({"message": "No data found for the provided job_id"}), 404
        return jsonify(data)
    else:
        return jsonify(list(users_cache.values()))

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)