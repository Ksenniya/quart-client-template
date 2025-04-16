```python
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass
import asyncio
import logging
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@dataclass
class HelloResponse:
    message: str

@dataclass
class ProcessRequest:
    input: str

@app.route('/api/hello', methods=['GET'])
@validate_querystring(HelloResponse)  # Workaround: validation first for GET requests
async def hello_world():
    return jsonify({"message": "Hello, World!"})

@app.route('/api/process', methods=['POST'])
@validate_request(ProcessRequest)  # Validation for POST requests
async def process_data(data: ProcessRequest):
    try:
        # Call external service to add item
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            entity={"input": data.input, "status": "processing"}
        )
        
        # Fire and forget the processing task
        await asyncio.create_task(process_entity(job_id, data.input))
        return jsonify({"result": f"Job {job_id} is being processed."}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "An error occurred while processing the data."}), 500

async def process_entity(job_id, data):
    # Simulate processing delay
    await asyncio.sleep(1)  # Simulate processing delay
    try:
        # Update item status to completed
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            entity={"input": data, "status": "completed"},
            technical_id=job_id,
            meta={}
        )
    except Exception as e:
        logger.exception(e)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```