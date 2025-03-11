import asyncio
import httpx
import logging
import time
import uuid

from quart import Quart, request, jsonify
from quart_schema import QuartSchema

app = Quart(__name__)
QuartSchema(app)  # initialize QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# In-memory caches (mock persistence)
pets_cache = {}      # {pet_id: pet_data}
orders_cache = {}    # {order_id: order_data}
users_cache = {}     # {user_id: user_data}
entity_jobs = {}     # {job_id: job_status}

# Asynchronous background process for entity work
async def process_entity(job, entity_data):
    try:
        # TODO: Replace this with real processing logic if needed.
        await asyncio.sleep(2)  # simulate processing delay
        # Modify entity_data as required during processing
        # For demonstration, we simply mark the job as completed.
        job["status"] = "completed"
        job["completedAt"] = time.time()
        logger.info(f"Processed entity data: {entity_data}")
    except Exception as e:
        logger.exception(e)
        job["status"] = "failed"

# Endpoint: Add a new pet
@app.route('/pet', methods=['POST'])
async def add_pet():
    try:
        data = await request.get_json()
        job_id = str(uuid.uuid4())
        # Mark the job as processing
        entity_jobs[job_id] = {"status": "processing", "requestedAt": time.time()}
        # Fire-and-forget processing task
        asyncio.create_task(process_entity(entity_jobs[job_id], data))
        # Use provided ID or generate one if missing
        pet_id = data.get("id", str(uuid.uuid4()))
        pets_cache[pet_id] = data
        logger.info(f"Added pet with id: {pet_id}")
        return jsonify({"job_id": job_id, "message": "Pet submission received and processing started"}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add pet"}), 500

# Endpoint: Find pets by status using external API
@app.route('/pet/findByStatus', methods=['POST'])
async def find_pet_by_status():
    try:
        request_data = await request.get_json()
        status_list = request_data.get("status", [])
        # Convert list to comma-separated string
        params = {'status': ','.join(status_list)}
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
async def place_order():
    try:
        data = await request.get_json()
        # Use provided order id or generate a new one
        order_id = data.get("id", str(uuid.uuid4()))
        orders_cache[order_id] = data
        logger.info(f"Order placed with id: {order_id}")
        return jsonify(data), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to place order"}), 500

# Endpoint: Create a new user
@app.route('/user', methods=['POST'])
async def create_user():
    try:
        data = await request.get_json()
        user_id = data.get("id", str(uuid.uuid4()))
        users_cache[user_id] = data
        logger.info(f"User created with id: {user_id}")
        # Return a subset of user info in the response
        user_response = {
            "id": data.get("id"),
            "username": data.get("username"),
            "firstName": data.get("firstName"),
            "lastName": data.get("lastName"),
            "email": data.get("email")
        }
        return jsonify(user_response), 200
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