Here's a prototype implementation based on the requirements you've specified. The code uses Quart for the web framework and httpx for asynchronous HTTP requests. It includes placeholders and TODO comments where necessary.

```python
import asyncio
import logging
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

# Initialize logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize the Quart app
app = Quart(__name__)
QuartSchema(app)

# In-memory cache to simulate persistence
entity_job = {}

# Simulated external API (placeholder for a real API)
EXTERNAL_API_URL = "https://api.example.com/process"  # TODO: Replace with a real API URL

async def process_entity(entity_id, input_data):
    try:
        # Simulate a processing task
        await asyncio.sleep(2)  # Simulate processing time

        # Simulate a call to an external API
        async with httpx.AsyncClient() as client:
            response = await client.post(EXTERNAL_API_URL, json={"data": input_data})
            if response.status_code == 200:
                result = response.json()
                # Process result here (if needed)
                logger.info(f"Processed data: {result}")
                entity_job[entity_id]["status"] = "completed"
            else:
                logger.error(f"External API error: {response.status_code}, {response.text}")
                entity_job[entity_id]["status"] = "failed"

    except Exception as e:
        logger.exception(e)
        entity_job[entity_id]["status"] = "error"

@app.route('/api/data', methods=['POST'])
async def submit_data():
    data = await request.get_json()

    entity_id = str(len(entity_job) + 1)  # Simple ID generation
    requested_at = request.date
    entity_job[entity_id] = {"status": "processing", "requestedAt": requested_at}

    # Fire and forget the processing task
    await asyncio.create_task(process_entity(entity_id, data))

    return jsonify({"result": "processing", "message": "Data is being processed", "id": entity_id}), 200

@app.route('/api/results', methods=['GET'])
async def get_results():
    return jsonify({"results": entity_job}), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```

### Key Points:
- **Logging**: Proper logging is included for success and error conditions.
- **In-Memory Cache**: The `entity_job` dictionary acts as a temporary data store.
- **Asynchronous Processing**: The `process_entity` function simulates a processing task that would involve an external API call.
- **Placeholder API**: A placeholder URL for an external API is included and marked with a TODO comment.
- **No Database**: The implementation avoids any external persistence or database solutions, as requested.

This prototype should help you verify the user experience and identify any gaps in the requirements before moving on to a more robust implementation.