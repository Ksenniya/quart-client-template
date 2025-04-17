Here’s the complete `app.py` file, incorporating the user suggestions and modifications as specified:

```python
from common.grpc_client.grpc_client import grpc_stream

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request
from dataclasses import dataclass
import logging
import asyncio
from datetime import datetime
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

app = Quart(__name__)
QuartSchema(app)

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class GreetRequest:
    name: str

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

@app.route('/hello', methods=['GET'])
async def hello():
    return jsonify({"message": "Hello World"}), 200

@app.route('/greet', methods=['POST'])
@validate_request(GreetRequest)
async def greet(data: GreetRequest):
    name = data.name.strip()

    if not name:
        return jsonify({"error": "Name is required."}), 400

    requested_at = datetime.now()
    entity_data = {"name": name, "requestedAt": requested_at.isoformat()}
    
    try:
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="greet_entity",
            entity_version=ENTITY_VERSION,
            entity=entity_data,
        )
        return jsonify({"message": f"Hello, {name}!", "job_id": job_id}), 200

    except Exception as e:
        logger.exception("Failed to process greet request: %s", e)
        return jsonify({"error": "Failed to process request."}), 500

@app.route('/items', methods=['GET'])
async def get_items():
    try:
        items = await entity_service.get_items()
        return jsonify(items), 200
    except Exception as e:
        logger.exception("Failed to retrieve items: %s", e)
        return jsonify({"error": "Failed to retrieve items."}), 500

@app.route('/items/<item_id>', methods=['GET'])
async def get_item(item_id):
    try:
        item = await entity_service.get_item(item_id)
        return jsonify(item), 200
    except Exception as e:
        logger.exception("Failed to retrieve item %s: %s", item_id, e)
        return jsonify({"error": "Failed to retrieve item."}), 500

@app.route('/items', methods=['PUT'])
async def update_item():
    data = await request.get_json()
    item_id = data.get("id")
    entity_data = data.get("entity")

    try:
        await entity_service.update_item(item_id=item_id, entity=entity_data, token=cyoda_token)
        return jsonify({"message": "Item updated successfully."}), 200
    except Exception as e:
        logger.exception("Failed to update item %s: %s", item_id, e)
        return jsonify({"error": "Failed to update item."}), 500

@app.route('/items/<item_id>', methods=['DELETE'])
async def delete_item(item_id):
    try:
        await entity_service.delete_item(item_id=item_id, token=cyoda_token)
        return jsonify({"message": "Item deleted successfully."}), 200
    except Exception as e:
        logger.exception("Failed to delete item %s: %s", item_id, e)
        return jsonify({"error": "Failed to delete item."}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```

### Key Features of This Version:
1. **Basic Greeting Endpoint**: The `/greet` endpoint allows for the addition of a new entity and returns the job ID.
2. **Item Retrieval**: The `/items` endpoint retrieves all items, while `/items/<item_id>` retrieves a specific item by ID.
3. **Update and Delete Functionality**: The `/items` endpoint for PUT requests allows updating an item, and the `/items/<item_id>` endpoint for DELETE requests allows deleting an item.
4. **Error Handling**: Each endpoint has error handling to log exceptions and return meaningful error messages.

This implementation reflects the user's requirements and suggestions. If you have further modifications or additional requests, please let me know!