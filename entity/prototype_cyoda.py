```python
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass
import logging
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token
import asyncio

app = Quart(__name__)
QuartSchema(app)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@dataclass
class GreetRequest:
    name: str

@app.route('/hello', methods=['GET'])
async def hello():
    return jsonify({"message": "Hello, World!"})

@app.route('/greet', methods=['POST'])
@validate_request(GreetRequest)  # Validation for POST must come last
async def greet(data: GreetRequest):
    name = data.name

    if not name:
        return jsonify({"error": "Name is required."}), 400

    # Process the greeting in a separate task
    requested_at = datetime.now()
    job_id = f"greet-{requested_at.timestamp()}"

    logger.info(f"Processing greeting for {name}...")

    # Fire and forget the processing task
    await asyncio.create_task(process_greeting(job_id, name))

    # Add item to external service and return the job_id
    id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="greeting",
        entity_version=ENTITY_VERSION,
        entity={"name": name}
    )

    return jsonify({"message": f"Hello, {name}!", "id": id})

@app.route('/greet_by_query', methods=['GET'])
@validate_querystring(GreetRequest)  # Workaround issue: Validation must come first for GET
async def greet_by_query():
    name = request.args.get('name')  # Standard approach to access parameters for GET requests

    if not name:
        return jsonify({"error": "Name is required."}), 400

    requested_at = datetime.now()
    job_id = f"greet-{requested_at.timestamp()}"

    logger.info(f"Processing greeting for {name}...")

    # Fire and forget the processing task
    await asyncio.create_task(process_greeting(job_id, name))

    # Add item to external service and return the job_id
    id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="greeting",
        entity_version=ENTITY_VERSION,
        entity={"name": name}
    )

    return jsonify({"message": f"Hello, {name}!", "id": id})

async def process_greeting(job_id, name):
    try:
        # Here we would retrieve the item from the external service if needed
        logger.info(f"Greeting processed for {name} successfully.")

    except Exception as e:
        logger.exception(e)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```