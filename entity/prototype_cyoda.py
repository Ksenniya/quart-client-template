```python
from quart import Quart, request
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass
import logging
import asyncio
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@dataclass
class Todo:
    task: str

# POST request to create a Todo
@app.route("/todo", methods=["POST"])
@validate_request(Todo)  # Validation for POST requests should be last
async def create_todo(data: Todo):
    requested_at = request.date
    entity_data = {"status": "processing", "requestedAt": requested_at, "task": data.task}
    
    try:
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="todo",
            entity_version=ENTITY_VERSION,
            entity=entity_data
        )
        logger.info(f"Created job {job_id} with task: {data.task}")
        
        # Fire and forget the processing task
        await asyncio.create_task(process_entity(job_id, entity_data))
        return {"job_id": job_id}, 201
    except Exception as e:
        logger.exception(e)
        return {"error": "Failed to create job"}, 500

# GET request to retrieve all Todos
@app.route("/todo", methods=["GET"])
@validate_querystring(Todo)  # Validation for GET requests should be first
async def get_todo():
    try:
        jobs = await entity_service.get_items(
            token=cyoda_token,
            entity_model="todo",
            entity_version=ENTITY_VERSION,
        )
        return {"jobs": jobs}, 200
    except Exception as e:
        logger.exception(e)
        return {"error": "Failed to retrieve jobs"}, 500

# Simple placeholder for processing entity
async def process_entity(job_id, data):
    # TODO: Add real processing logic here
    await asyncio.sleep(5)  # Simulate processing time
    logger.info(f"Processed entity with job_id: {job_id} and data: {data}")

# Example of a GET request with path parameter
@app.route("/companies/<string:id>/lei", methods=["GET"])
async def get_lei(id: str):
    # No validation needed for this endpoint
    # TODO: Implement logic to retrieve LEI based on company ID
    return {"company_id": id, "lei": "mock_lei_value"}, 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```