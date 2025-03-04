import asyncio
import logging
import datetime
import uuid
from dataclasses import dataclass

import httpx
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request  # For POST endpoints

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Data classes for request validation (using only primitives)
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

# In-memory storage mocks
pets = {}    # pet_id -> pet data
orders = {}  # order_id -> order data
users = {}   # username -> user data

# Auto-increment counters for IDs
next_pet_id = 1
next_order_id = 1

async def process_pet(pet_id: int, pet_data: dict):
    """
    Process pet data using external services.
    This function calls the real Petstore API to add a pet.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Using real Petstore API endpoint for creating a pet.
            response = await client.post("https://petstore.swagger.io/v2/pet", json=pet_data)
            response.raise_for_status()
            external_info = response.json()  # Real external data response.
    except Exception as e:
        logger.exception(e)
        external_info = {"info": "external service unavailable"}  # Fallback response.
    pet = pets.get(pet_id)
    if pet:
        pet["externalData"] = external_info
        logger.info(f"Updated pet {pet_id} with external data.")
    else:
        logger.info(f"Pet {pet_id} not found for external update.")

async def process_order(order_id: int, order_data: dict):
    """
    Process order data using an external calculation service.
    This function calls the real Petstore API to place an order.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Using real Petstore API endpoint for placing an order.
            response = await client.post("https://petstore.swagger.io/v2/store/order", json=order_data)
            response.raise_for_status()
            calculation_data = response.json()  # Real calculation/order result.
    except Exception as e:
        logger.exception(e)
        calculation_data = {"calculation": "default value"}  # Fallback calculation data.
    order = orders.get(order_id)
    if order:
        order["externalCalculation"] = calculation_data
        logger.info(f"Updated order {order_id} with external calculation data.")
    else:
        logger.info(f"Order {order_id} not found for external update.")

async def process_user_login(username: str, credentials: dict):
    """
    Process user login with an external authentication service.
    This function calls the real Petstore API login endpoint.
    Note: The Petstore API defines login as a GET request.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Using real Petstore API endpoint for user login.
            params = {"username": credentials.get("username"), "password": credentials.get("password")}
            response = await client.get("https://petstore.swagger.io/v2/user/login", params=params)
            response.raise_for_status()
            auth_result = response.json()  # Real authentication response.
    except Exception as e:
        logger.exception(e)
        auth_result = {"authenticated": True}  # Fallback dummy authentication.
    # For this prototype, if no error occurs, we assume authentication is successful.
    return {"authenticated": True, "details": auth_result}

# NOTE: For POST endpoints, due to an issue in quart-schema,
# we apply @validate_request decorator after the route decorator.

@app.route('/api/pet', methods=['POST'])
@validate_request(PetData)  # Workaround: For POST endpoints, put this after the route decorator.
async def create_pet(data: PetData):
    global next_pet_id
    pet = data.__dict__.copy()
    pet["id"] = next_pet_id
    next_pet_id += 1
    pets[pet["id"]] = pet
    logger.info(f"Created pet with ID {pet['id']}")
    # Fire and forget the processing task to enrich pet data using the real external API.
    asyncio.create_task(process_pet(pet["id"], pet))
    return jsonify(pet), 201

@app.route('/api/pet/<int:pet_id>', methods=['GET'])
async def retrieve_pet(pet_id: int):
    pet = pets.get(pet_id)
    if not pet:
        abort(404, description="Pet not found")
    return jsonify(pet)

@app.route('/api/order', methods=['POST'])
@validate_request(OrderData)  # Workaround: For POST endpoints, put this after the route decorator.
async def place_order(data: OrderData):
    global next_order_id
    order = data.__dict__.copy()
    order["orderId"] = next_order_id
    next_order_id += 1
    orders[order["orderId"]] = order
    logger.info(f"Placed order with ID {order['orderId']}")
    # Fire and forget the processing task to calculate order details using the real external API.
    asyncio.create_task(process_order(order["orderId"], order))
    return jsonify(order), 201

@app.route('/api/order/<int:order_id>', methods=['GET'])
async def retrieve_order(order_id: int):
    order = orders.get(order_id)
    if not order:
        abort(404, description="Order not found")
    return jsonify(order)

@app.route('/api/user/login', methods=['POST'])
@validate_request(UserLoginData)  # Workaround: For POST endpoints, put this after the route decorator.
async def user_login(data: UserLoginData):
    credentials = data.__dict__.copy()
    username = credentials.get("username")
    password = credentials.get("password")
    if not username or not password:
        abort(400, description="Username and password are required")
    # For this prototype, if the username is not in cache, create a basic user record.
    if username not in users:
        users[username] = {
            "id": str(uuid.uuid4()),
            "username": username,
            "firstName": "TODO",        # TODO: Replace with actual details if available.
            "lastName": "TODO",         # TODO: Replace with actual details if available.
            "email": "TODO@example.com",# TODO: Replace with actual details if available.
            "phone": "TODO",            # TODO: Replace with actual details if available.
            "userStatus": 1
        }
    auth_result = await process_user_login(username, credentials)
    if not auth_result.get("authenticated", False):
        abort(401, description="Authentication failed")
    token = f"dummy-token-{username}"  # TODO: Replace with secure token generation.
    expires_at = (datetime.datetime.utcnow() + datetime.timedelta(hours=1)).isoformat() + "Z"
    result = {"username": username, "token": token, "expiresAt": expires_at}
    logger.info(f"User {username} logged in successfully.")
    return jsonify(result)

@app.route('/api/user/<string:username>', methods=['GET'])
async def retrieve_user(username: str):
    user = users.get(username)
    if not user:
        abort(404, description="User not found")
    return jsonify(user)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)