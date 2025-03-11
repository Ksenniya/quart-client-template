import asyncio
import logging
import datetime
from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import httpx

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

app = Quart(__name__)
QuartSchema(app)

# Local cache to mock persistence for orders and user sessions
orders_cache = {}
user_sessions = {}

# External API Base URL
PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

###############################
# Helper: Process Order Task
###############################
async def process_order(order_id, order_data):
    try:
        logger.info(f"Started processing order {order_id}")
        # TODO: Replace with real processing business logic
        await asyncio.sleep(2)  # Simulate processing delay
        orders_cache[order_id]["status"] = "processed"
        logger.info(f"Order {order_id} processed")
    except Exception as e:
        logger.exception(e)

###############################
# Endpoint: User Login
###############################
@app.route('/api/user/login', methods=['POST'])
async def user_login():
    try:
        data = await request.get_json()
        username = data.get("username")
        password = data.get("password")
        if not username or not password:
            return jsonify({"error": "username and password required"}), 400

        # External API for login is defined as GET, so using httpx.AsyncClient for this call
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{PETSTORE_BASE_URL}/user/login", params={"username": username, "password": password})
            response.raise_for_status()
            # External API returns a token as a string; wrapping it into a JSON object for our needs.
            token = response.text
            user_sessions[username] = {"token": token, "loggedInAt": datetime.datetime.utcnow().isoformat()}
            return jsonify({"token": token})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500

###############################
# Endpoint: Fetch Pets by Status
###############################
@app.route('/api/pets/status', methods=['POST'])
async def fetch_pets_by_status():
    try:
        data = await request.get_json()
        statuses = data.get("status")
        if not statuses or not isinstance(statuses, list):
            return jsonify({"error": "status field must be a list"}), 400
        
        # Building the query parameters for external API (GET /pet/findByStatus)
        params = [("status", status) for status in statuses]
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params)
            response.raise_for_status()
            pets = response.json()
            return jsonify({"pets": pets})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500

###############################
# Endpoint: Fetch Pets by Tags
###############################
@app.route('/api/pets/tags', methods=['POST'])
async def fetch_pets_by_tags():
    try:
        data = await request.get_json()
        tags = data.get("tags")
        if not tags or not isinstance(tags, list):
            return jsonify({"error": "tags field must be a list"}), 400

        # Building the query parameters for external API (GET /pet/findByTags - deprecated but used here)
        params = [("tags", tag) for tag in tags]

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{PETSTORE_BASE_URL}/pet/findByTags", params=params)
            response.raise_for_status()
            pets = response.json()
            return jsonify({"pets": pets})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500

###############################
# Endpoint: Get Pet by ID
###############################
@app.route('/api/pets/<int:petId>', methods=['POST'])
async def get_pet_by_id(petId):
    try:
        # No additional JSON payload is required as petId is in the URL.
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{PETSTORE_BASE_URL}/pet/{petId}")
            if response.status_code == 404:
                return jsonify({"error": "Pet not found"}), 404
            response.raise_for_status()
            pet = response.json()
            return jsonify(pet)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500

###############################
# Endpoint: Place Order for a Pet
###############################
@app.route('/api/order', methods=['POST'])
async def place_order():
    try:
        data = await request.get_json()
        pet_id = data.get("petId")
        quantity = data.get("quantity", 1)
        if not pet_id:
            return jsonify({"error": "petId is required"}), 400

        # Creating an order object based on the external API model.
        order = {
            "petId": pet_id,
            "quantity": quantity,
            "shipDate": datetime.datetime.utcnow().isoformat() + "Z",
            "status": "placed",
            "complete": False
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(f"{PETSTORE_BASE_URL}/store/order", json=order)
            response.raise_for_status()
            order_response = response.json()

            order_id = order_response.get("id")
            if not order_id:
                # Fallback if external API does not provide an id -- TODO: refine logic as needed
                order_id = len(orders_cache) + 1
                order_response["id"] = order_id

            # Store order in local cache with additional metadata.
            orders_cache[order_id] = {
                "status": "processing",
                "requestedAt": datetime.datetime.utcnow().isoformat(),
                "order": order_response
            }
            # Fire-and-forget processing task.
            asyncio.create_task(process_order(order_id, order_response))
            return jsonify(order_response)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500

###############################
# Entry Point
###############################
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)