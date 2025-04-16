```python
import logging
from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize Quart app
app = Quart(__name__)
QuartSchema(app)

@dataclass
class GreetRequest:
    name: str

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@app.route('/hello', methods=['GET'])
async def get_hello():
    """Retrieve a simple greeting message."""
    return jsonify({"message": "Hello, World!"})

async def process_greetings(entity_data):
    """Process the entity data before persistence."""
    # Modify the entity state directly
    entity_data["processedAt"] = datetime.now().isoformat()
    
    # Log the processing
    logger.info(f"Processing greeting for {entity_data['name']}.")

    # Simulate an asynchronous task (e.g., fetching supplementary data)
    # For example, here we could add a secondary entity or log information
    # Note: entity_service.add_item cannot be called for the same entity model
    # but we can prepare and log supplementary data if needed.

    # If you need to retrieve supplementary data, you could do so here
    # However, ensure it is for a different entity_model
    # e.g., supplementary_data = await entity_service.get_some_data(...)
    
    return entity_data

@app.route('/greet', methods=['POST'])
@validate_request(GreetRequest)
async def post_greet(data: GreetRequest):
    """Accept a name and return a personalized greeting message."""
    name = data.name

    # Log the incoming request
    logger.info(f"Received request to greet {name}.")

    personalized_message = f"Hello, {name}!"

    # Prepare the data to be sent to the entity service
    entity_data = {
        "message": personalized_message,
        "requestedAt": datetime.now().isoformat(),
        "name": name
    }

    # Adding item to the external entity service
    try:
        id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="greetings",
            entity_version=ENTITY_VERSION,
            entity=entity_data,
            workflow=process_greetings  # Adding the workflow function
        )
        logger.info(f"Greeting generated and stored for {name}: {personalized_message}, ID: {id}")
        return jsonify({"message": personalized_message, "id": id})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to generate greeting."}), 500

@app.route('/greet', methods=['GET'])
@validate_querystring(GreetRequest)
async def get_greet():
    """Retrieve a personalized greeting message based on query parameters."""
    name = request.args.get('name')

    if not name:
        return jsonify({"error": "Name parameter is required."}), 400

    logger.info(f"Retrieving greeting for {name}.")

    # Retrieve the greeting from the entity service
    try:
        items = await entity_service.get_items_by_condition(
            token=cyoda_token,
            entity_model="greetings",
            entity_version=ENTITY_VERSION,
            condition={"name": name}
        )

        if items:
            message = items[0]["message"]
        else:
            message = "Hello, Guest!"

        return jsonify({"message": message})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve greeting."}), 500

# Entry point for running the app
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```