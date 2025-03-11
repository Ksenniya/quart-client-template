import asyncio
import datetime
import logging
from dataclasses import dataclass

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request
import httpx

from common.config.config import ENTITY_VERSION  # always use this constant
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

app = Quart(__name__)
QuartSchema(app)

# Startup initialization for cyoda
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Dataclass models for request validation
@dataclass
class UserLogin:
    username: str
    password: str

@dataclass
class PetStatusRequest:
    status: list  # list of status strings

@dataclass
class PetTagsRequest:
    tags: list  # list of tag strings

@dataclass
class PlaceOrderRequest:
    petId: int
    quantity: int = 1

# Removed local caches (orders_cache and user_sessions) in favor of entity_service

###############################
# Helper: Process Order Task
###############################
async def process_order(order_id, order_data):
    try:
        logger.info(f"Started processing order {order_id}")
        # TODO: Replace with real processing business logic
        await asyncio.sleep(2)  # Simulate processing delay
        # Update the order status to "processed" using entity_service update_item
        order_update = order_data.copy()
        order_update["status"] = "processed"
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="order",
            entity_version=ENTITY_VERSION,
            entity=order_update,
            technical_id=order_id,
            meta={}
        )
        logger.info(f"Order {order_id} processed")
    except Exception as e:
        logger.exception(e)

###############################
# Endpoint: User Login
###############################
@app.route('/api/user/login', methods=['POST'])
@validate_request(UserLogin)
async def user_login(data: UserLogin):
    try:
        username = data.username
        password = data.password
        if not username or not password:
            return jsonify({"error": "username and password required"}), 400

        # External API for login is defined as GET, so using httpx.AsyncClient for this call
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://petstore.swagger.io/v2/user/login",
                params={"username": username, "password": password}
            )
            response.raise_for_status()
            # External API returns a token as a string; wrapping it into a JSON object for our needs.
            token = response.text
            # Save session using entity_service instead of local in‑memory cache.
            session_data = {
                "username": username,
                "token": token,
                "loggedInAt": datetime.datetime.utcnow().isoformat()
            }
            # Call external service to add user session; response (id) is ignored.
            await entity_service.add_item(
                token=cyoda_token,
                entity_model="user_session",
                entity_version=ENTITY_VERSION,
                entity=session_data
            )
            return jsonify({"token": token})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500

###############################
# Endpoint: Fetch Pets by Status
###############################
@app.route('/api/pets/status', methods=['POST'])
@validate_request(PetStatusRequest)
async def fetch_pets_by_status(data: PetStatusRequest):
    try:
        statuses = data.status
        if not statuses or not isinstance(statuses, list):
            return jsonify({"error": "status field must be a list"}), 400
        
        # Building the query parameters for external API (GET /pet/findByStatus)
        params = [("status", status) for status in statuses]
        
        async with httpx.AsyncClient() as client:
            response = await client.get("https://petstore.swagger.io/v2/pet/findByStatus", params=params)
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
@validate_request(PetTagsRequest)
async def fetch_pets_by_tags(data: PetTagsRequest):
    try:
        tags = data.tags
        if not tags or not isinstance(tags, list):
            return jsonify({"error": "tags field must be a list"}), 400

        # Building the query parameters for external API (GET /pet/findByTags - deprecated but used here)
        params = [("tags", tag) for tag in tags]

        async with httpx.AsyncClient() as client:
            response = await client.get("https://petstore.swagger.io/v2/pet/findByTags", params=params)
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
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://petstore.swagger.io/v2/pet/{petId}")
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
@validate_request(PlaceOrderRequest)
async def place_order(data: PlaceOrderRequest):
    try:
        pet_id = data.petId
        quantity = data.quantity
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

        # Place order using external petstore API
        async with httpx.AsyncClient() as client:
            response = await client.post("https://petstore.swagger.io/v2/store/order", json=order)
            response.raise_for_status()
            order_response = response.json()

            order_id = order_response.get("id")
            if not order_id:
                # Fallback if external API does not provide an id -- refine logic as needed
                order_id = 1  # In real-world you might need a better fallback,
                             # but here we use a constant value for demonstration.
                order_response["id"] = order_id

            # Save order using external service instead of local in‑memory cache.
            order_id = await entity_service.add_item(
                token=cyoda_token,
                entity_model="order",
                entity_version=ENTITY_VERSION,
                entity=order_response
            )
            # Fire-and-forget processing task.
            asyncio.create_task(process_order(order_id, order_response))
            # Return only the id as the creation response.
            return jsonify({"id": order_id})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500

###############################
# Entry Point
###############################
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)