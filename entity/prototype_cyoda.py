```python
import asyncio
import logging
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

# Initialize logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize the Quart app
app = Quart(__name__)
QuartSchema(app)

# In-memory cache has been removed; now using external service

@dataclass
class InputData:
    inputData: str
    additionalParam: str

@dataclass
class ResultData:
    results: list

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

async def process_entity(entity_id, input_data):
    try:
        # Simulate a processing task
        await asyncio.sleep(2)  # Simulate processing time

        # Simulate a call to an external API (if needed, otherwise can be removed)
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(EXTERNAL_API_URL, json={"data": input_data})
        #     if response.status_code == 200:
        #         result = response.json()
        #         # Process result here (if needed)
        #         logger.info(f"Processed data: {result}")
        #     else:
        #         logger.error(f"External API error: {response.status_code}, {response.text}")

        # Mark entity as processed in external service
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            entity={"status": "completed"},
            technical_id=entity_id,
            meta={}
        )

    except Exception as e:
        logger.exception(e)
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            entity={"status": "error"},
            technical_id=entity_id,
            meta={}
        )

@app.route('/api/data', methods=['POST'])
@validate_request(InputData)  # Validation is performed last for POST requests
async def submit_data(data: InputData):
    entity_id = str(len(entity_job) + 1)  # Simple ID generation, can be replaced with an external call
    requested_at = request.date

    # Add item to external service
    await entity_service.add_item(
        token=cyoda_token,
        entity_model="entity_job",
        entity_version=ENTITY_VERSION,
        entity={"status": "processing", "requestedAt": requested_at}
    )

    # Fire and forget the processing task
    await asyncio.create_task(process_entity(entity_id, data.inputData))

    return jsonify({"result": "processing", "message": "Data is being processed", "id": entity_id}), 200

@app.route('/api/results', methods=['GET'])
@validate_querystring(ResultData)  # Validation is performed first for GET requests
async def get_results():
    results = await entity_service.get_items(
        token=cyoda_token,
        entity_model="entity_job",
        entity_version=ENTITY_VERSION,
    )
    return jsonify({"results": results}), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```