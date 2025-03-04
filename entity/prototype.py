import asyncio
import logging
import datetime
import uuid

import httpx
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# In-memory storage mocks
pets = {}       # pet_id -> pet data
orders = {}     # order_id -> order data
users = {}      # username -> user data

# Auto-increment counters for IDs
next_pet_id = 1
next_order_id = 1
# For simplicity, users will be keyed by username when created externally


async def process_pet(pet_id: int, pet_data: dict):
    """
    Process pet data using external services.
    This function simulates an external API call to enrich pet data.
    """
    try:
        async with httpx.AsyncClient() as client:
            # TODO: Replace the URL with the actual external API endpoint if available.
            response = await client.post("http://example.com/external/pet", json=pet_data)
            # TODO: Process the actual external response.
            external_info = response.json()  # Simulated external data response.
    except Exception as e:
        logger.exception(e)
        # Fallback to a dummy response in case of error.
        external_info = {"info": "external service unavailable"}
    # Update the pet entry with external data.
    pet = pets.get(pet_id)
    if pet:
        pet["externalData"] = external_info
        logger.info(f"Updated pet {pet_id} with external data.")
    else:
        logger.info(f"Pet {pet_id} not found for external update.")


async def process_order(order_id: int, order_data: dict):
    """
    Process order data using an external calculation service.
    This function simulates an external API call to perform necessary validations and computations.
    """
    try:
        async with httpx.AsyncClient() as client:
            # TODO: Replace the URL with the actual external calculation service URL.
            response = await client.post("http://example.com/external/order/calc", json=order_data)
            # TODO: Process the actual external calculation response.
            calculation_data = response.json()  # Simulated external calculation result.
    except Exception as e:
        logger.exception(e)
        # Fallback to dummy calculation data.
        calculation_data = {"calculation": "default value"}
    # Update the order entry with external calculation data.
    order = orders.get(order_id)
    if order:
        order["externalCalculation"] = calculation_data
        logger.info(f"Updated order {order_id} with external calculation data.")
    else:
        logger.info(f"Order {order_id} not found for external update.")


async def process_user_login(username: str, credentials: dict):
    """
    Process user login with an external authentication service.
    This function simulates an external API call for user authentication.
    """
    try:
        async with httpx.AsyncClient() as client:
            # TODO: Replace the URL with the actual external authentication service URL.
            response = await client.post("http://example.com/external/auth", json=credentials)
            auth_result = response.json()  # Simulated response
    except Exception as e:
        logger.exception(e)
        # Fallback to a dummy authentication result if external auth is not available.
        auth_result = {"authenticated": True}
    return auth_result


@app.route('/api/pet', methods=['POST'])
async def create_pet():
    global next_pet_id
    data = await request.get_json()
    if not data:
        abort(400, description="Invalid request body")
    pet = data.copy()
    pet["id"] = next_pet_id
    next_pet_id += 1
    pets[pet["id"]] = pet
    logger.info(f"Created pet with ID {pet['id']}")
    # Fire and forget the processing task to enrich pet data using external API.
    asyncio.create_task(process_pet(pet["id"], pet))
    return jsonify(pet), 201


@app.route('/api/pet/<int:pet_id>', methods=['GET'])
async def retrieve_pet(pet_id: int):
    pet = pets.get(pet_id)
    if not pet:
        abort(404, description="Pet not found")
    return jsonify(pet)


@app.route('/api/order', methods=['POST'])
async def place_order():
    global next_order_id
    data = await request.get_json()
    if not data:
        abort(400, description="Invalid request body")
    order = data.copy()
    order["orderId"] = next_order_id
    next_order_id += 1
    orders[order["orderId"]] = order
    logger.info(f"Placed order with ID {order['orderId']}")
    # Fire and forget the processing task to calculate order details using external API.
    asyncio.create_task(process_order(order["orderId"], order))
    return jsonify(order), 201


@app.route('/api/order/<int:order_id>', methods=['GET'])
async def retrieve_order(order_id: int):
    order = orders.get(order_id)
    if not order:
        abort(404, description="Order not found")
    return jsonify(order)


@app.route('/api/user/login', methods=['POST'])
async def user_login():
    data = await request.get_json()
    if not data:
        abort(400, description="Invalid request body")
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        abort(400, description="Username and password are required")
    # TODO: Implement real user lookup and password validation if needed.
    # For this prototype, assume the user is valid if they don't already exist in our local cache.
    if username not in users:
        # Create a new user with minimum details.
        users[username] = {
            "id": str(uuid.uuid4()),
            "username": username,
            "firstName": "TODO",     # TODO: Replace with actual user details if available.
            "lastName": "TODO",      # TODO: Replace with actual user details if available.
            "email": "TODO@example.com",  # TODO: Replace with actual user details if available.
            "phone": "TODO",         # TODO: Replace with actual user details if available.
            "userStatus": 1
        }
    # Process external authentication.
    auth_result = await process_user_login(username, data)
    if not auth_result.get("authenticated", False):
        abort(401, description="Authentication failed")
    # Generate a dummy token. In production, implement secure token generation.
    token = f"dummy-token-{username}"
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