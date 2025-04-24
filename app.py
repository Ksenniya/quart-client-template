To add notification logic to the greet entity in the provided `app.py` code, we'll implement the logic to send a notification after the greeting entity is created. This will involve using the `entity_service` to handle notifications appropriately.

Here's the updated code for `app.py`, incorporating the notification logic:

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
        # Add the greet entity
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="greet_entity",
            entity_version=ENTITY_VERSION,
            entity=entity_data,
        )
        
        # Prepare notification data
        notification_data = {
            "job_id": job_id,
            "message": f"Hello, {name}!",
            "timestamp": requested_at.isoformat()
        }

        # Send notification (you would replace this with actual notification logic)
        await send_notification(notification_data)

        return jsonify({"message": f"Hello, {name}!", "job_id": job_id}), 200

    except Exception as e:
        logger.exception("Failed to process greet request: %s", e)
        return jsonify({"error": "Failed to process request."}), 500

async def send_notification(data: dict):
    # Here you can implement the actual notification logic
    # For example, send an email or a message to a message queue
    logger.info(f"Notification sent: {data}")

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```

### Key Changes Made:
1. **Notification Logic**: After successfully adding the greet entity, a `send_notification` function is called to handle the notification logic.
2. **Notification Function**: The `send_notification` function is defined to log the notification data. You can replace the logging with actual notification logic (e.g., sending an email or a message to a service).

This updated code incorporates the notification logic into the greet entity workflow while maintaining the rest of the functionality. If you need further modifications or additional features, please let me know!