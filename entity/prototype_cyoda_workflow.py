```python
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass
import logging
from datetime import datetime
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

app = Quart(__name__)
QuartSchema(app)

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@dataclass
class GreetRequest:
    name: str

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

async def process_greet_entity(entity_data):
    # Example processing function that modifies entity data
    entity_data['processed'] = True
    
    # Simulating an async task (could be a call to another service, etc.)
    await asyncio.sleep(1)  # Represents an async operation

    # You can also add supplementary data entities here if needed
    # e.g., await entity_service.add_item(...) for different entity_model
    
    return entity_data

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
            workflow=process_greet_entity  # Added workflow function
        )
        return jsonify({"message": f"Hello, {name}!", "job_id": job_id}), 200

    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to process request."}), 500

@app.route('/greet/query', methods=['GET'])
@validate_querystring(GreetRequest)
async def greet_query():
    name = request.args.get('name', '').strip()

    if not name:
        return jsonify({"error": "Name is required."}), 400

    return jsonify({"message": f"Hello, {name}!"}), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```