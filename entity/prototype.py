```python
import asyncio
import logging
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

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

@dataclass
class InputData:
    inputData: str
    additionalParam: str

@dataclass
class ResultData:
    results: list

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
@validate_request(InputData)  # Validation is performed last for POST requests
async def submit_data(data: InputData):
    entity_id = str(len(entity_job) + 1)  # Simple ID generation
    requested_at = request.date
    entity_job[entity_id] = {"status": "processing", "requestedAt": requested_at}

    # Fire and forget the processing task
    await asyncio.create_task(process_entity(entity_id, data.inputData))

    return jsonify({"result": "processing", "message": "Data is being processed", "id": entity_id}), 200

@app.route('/api/results', methods=['GET'])
@validate_querystring(ResultData)  # Validation is performed first for GET requests
async def get_results():
    return jsonify({"results": entity_job}), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```