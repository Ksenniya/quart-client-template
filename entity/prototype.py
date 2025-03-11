from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

app = Quart(__name__)
QuartSchema(app)

# Dataclass definitions for request bodies
@dataclass
class StatusQuery:
    status: str  # Comma-separated statuses (e.g., "available,pending")

@dataclass
class PetRequest:
    name: str
    status: str
    photoUrls: str  # Comma-separated photo URLs
    categoryId: int
    categoryName: str

@dataclass
class OrderRequest:
    petId: int
    quantity: int
    status: str

# POST endpoint to fetch pets by status
# Note: External data retrieval is done in POST endpoints per requirements.
@app.route("/api/pets/status", methods=["POST"])
@validate_request(StatusQuery)  # Workaround: for POST, validation is after route decorator.
async def fetch_pets_by_status(data: StatusQuery):
    statuses = [s.strip() for s in data.status.split(",")]
    # Invoke external data source (Pet Store API) and filter by statuses.
    # This is a stubbed response for illustration.
    pets = [
        {"id": 1, "name": "Doggie", "status": "available", "photoUrls": ["url1", "url2"]},
        {"id": 2, "name": "Kitty", "status": "pending", "photoUrls": ["url3", "url4"]}
    ]
    filtered_pets = [pet for pet in pets if pet["status"] in statuses]
    return jsonify({"pets": filtered_pets})

# POST endpoint to add a new pet
@app.route("/api/pets", methods=["POST"])
@validate_request(PetRequest)  # Workaround: for POST, validation is after route decorator.
async def add_new_pet(data: PetRequest):
    # Stub: simulate adding a pet and returning pet details.
    new_pet = {
        "id": 123,  # Simulated new pet id
        "name": data.name,
        "status": data.status,
        "photoUrls": [url.strip() for url in data.photoUrls.split(",")],
        "category": {"id": data.categoryId, "name": data.categoryName}
    }
    return jsonify(new_pet)

# GET endpoint to retrieve pet details by petId (no request validation needed)
@app.route("/api/pets/<int:petId>", methods=["GET"])
async def get_pet_details(petId: int):
    # Stub: simulate fetching pet details
    pet = {
        "id": petId,
        "name": "Doggie",
        "status": "available",
        "photoUrls": ["url1", "url2"]
    }
    return jsonify(pet)

# POST endpoint to place an order for a pet
@app.route("/api/orders", methods=["POST"])
@validate_request(OrderRequest)  # Workaround: for POST, validation is after route decorator.
async def place_order(data: OrderRequest):
    # Stub: simulate order placement
    order = {
        "id": 456,  # Simulated order id
        "petId": data.petId,
        "quantity": data.quantity,
        "status": data.status
    }
    return jsonify(order)

# GET endpoint to retrieve order details by orderId (no request validation needed)
@app.route("/api/orders/<int:orderId>", methods=["GET"])
async def get_order_details(orderId: int):
    # Stub: simulate fetching order details
    order = {
        "id": orderId,
        "petId": 123,
        "quantity": 1,
        "status": "placed"
    }
    return jsonify(order)

# GET endpoint with query parameters example using validation.
# Note: GET endpoints with query validation require the validation decorator to be applied first.
@validate_querystring(StatusQuery)  # Workaround: For GET queries, validation decorator is placed first.
@app.route("/api/pets/query", methods=["GET"])
async def query_pets():
    # Access parameters using standard approach.
    status = request.args.get('status', '')
    # Convert comma-separated status string into a list.
    statuses = [s.strip() for s in status.split(",") if s.strip()]
    # Stub: simulate external data retrieval.
    pets = [
        {"id": 1, "name": "Doggie", "status": "available", "photoUrls": ["url1", "url2"]},
        {"id": 2, "name": "Kitty", "status": "pending", "photoUrls": ["url3", "url4"]}
    ]
    filtered_pets = [pet for pet in pets if pet["status"] in statuses] if statuses else pets
    return jsonify({"pets": filtered_pets})

if __name__ == "__main__":
    app.run()