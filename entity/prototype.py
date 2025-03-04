import asyncio
import datetime
import logging
import uuid

from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory caches for prototype purposes.
pet_search_cache = {}   # key: job_id, value: {"status": ..., "requestedAt": ..., "results": ...}
orders_cache = {}       # key: job_id, value: order details or error message
users_cache = {}        # key: username, value: user info (e.g. token, expiration)

async def process_pet_search(job_id, filter_data):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Determine external API endpoint parameters based on provided filter.
            status = filter_data.get("status")
            if isinstance(status, list):
                status_param = ",".join(status)
            else:
                status_param = status

            # TODO: Extend logic to handle tag filtering using /pet/findByTags if needed.
            external_url = "https://petstore.swagger.io/v2/pet/findByStatus"
            params = {"status": status_param}
            response = await client.get(external_url, params=params)
            results = response.json()

            pet_search_cache[job_id]["results"] = results
            pet_search_cache[job_id]["status"] = "completed"
            logger.info(f"Pet search job {job_id} completed")
    except Exception as e:
        logger.exception(e)
        pet_search_cache[job_id]["status"] = "failed"
        pet_search_cache[job_id]["error"] = str(e)

async def process_order_create(job_id, order_data):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            external_url = "https://petstore.swagger.io/v2/store/order"
            response = await client.post(external_url, json=order_data)
            result = response.json()
            orders_cache[job_id] = result
            logger.info(f"Order job {job_id} completed")
    except Exception as e:
        logger.exception(e)
        orders_cache[job_id] = {"error": str(e)}

@app.route('/api/pets/find', methods=['POST'])
async def find_pets():
    data = await request.get_json()
    job_id = str(uuid.uuid4())
    pet_search_cache[job_id] = {
        "status": "processing",
        "requestedAt": datetime.datetime.utcnow().isoformat(),
        "results": None
    }
    # Fire and forget the pet search processing task.
    asyncio.create_task(process_pet_search(job_id, data))
    return jsonify({"job_id": job_id, "status": "processing"})

@app.route('/api/pets/results', methods=['GET'])
async def get_pet_results():
    job_id = request.args.get("job_id")
    if not job_id or job_id not in pet_search_cache:
        return jsonify({"error": "Invalid or missing job_id"}), 400
    return jsonify(pet_search_cache[job_id])

@app.route('/api/orders/create', methods=['POST'])
async def create_order():
    data = await request.get_json()
    job_id = str(uuid.uuid4())
    orders_cache[job_id] = {
        "status": "processing",
        "requestedAt": datetime.datetime.utcnow().isoformat()
    }
    # Fire and forget the order processing task.
    asyncio.create_task(process_order_create(job_id, data))
    return jsonify({"job_id": job_id, "status": "processing"})

@app.route('/api/orders/<order_id>', methods=['GET'])
async def get_order(order_id: str):
    if order_id not in orders_cache:
        return jsonify({"error": "Order not found"}), 404
    return jsonify(orders_cache[order_id])

@app.route('/api/users/login', methods=['POST'])
async def user_login():
    data = await request.get_json()
    username = data.get("username")
    password = data.get("password")
    # TODO: Replace with real authentication and optional external validation logic.
    if username == "user1" and password == "secret":
        token = str(uuid.uuid4())
        user_info = {
            "username": username,
            "token": token,
            "expires": (datetime.datetime.utcnow() + datetime.timedelta(hours=1)).isoformat()
        }
        users_cache[username] = user_info
        return jsonify(user_info)
    else:
        return jsonify({"error": "Invalid username or password"}), 401

@app.route('/api/users/<username>', methods=['GET'])
async def get_user(username: str):
    user_info = users_cache.get(username)
    if not user_info:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user_info)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)