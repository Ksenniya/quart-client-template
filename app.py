To fulfill the user's request of removing all endpoints other than "greet" from the `app.py` file and incorporating the specified functionalities, here’s the updated code:

```python
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request
from dataclasses import dataclass
import logging
import asyncio
from datetime import datetime
from common.config.config import ENTITY_VERSION
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

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```

### Key Changes Made:
1. **Removed Unused Endpoints**: All endpoints except for the `/greet` endpoint have been removed.
2. **Greet Endpoint**: The `/greet` endpoint now handles the addition of an item and returns the job ID along with a greeting message.
3. **Error Handling and Logging**: The error handling and logging remain intact for the `/greet` endpoint.

This updated code meets the user's requirement to keep only the "greet" functionality in the `app.py` file. If you need any further modifications or additional features, please let me know!