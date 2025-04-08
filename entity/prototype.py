```python
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass
import httpx
import logging
import asyncio

app = Quart(__name__)
QuartSchema(app)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Placeholder for local cache
entity_job = {}

@dataclass
class Todo:
    task: str

# POST request
@app.route("/test", methods=["POST"])
@validate_request(Todo)  # Validation should be last in POST
async def create_todo(data: Todo):
    requested_at = asyncio.get_event_loop().time()
    job_id = f"job-{requested_at}"
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}
    
    # Fire and forget the processing task
    await asyncio.create_task(process_entity(entity_job, data.__dict__))
    
    return jsonify({"job_id": job_id}), 201

# Mock processing function
async def process_entity(entity_job, data):
    # TODO: Implement actual processing logic
    logger.info(f"Processing entity: {data}")
    await asyncio.sleep(2)  # Simulate processing time
    entity_job[data["job_id"]]["status"] = "completed"

# GET request with request parameters
@app.route("/test", methods=["GET"])
@validate_querystring(Todo)  # Validation must be first in GET
async def get_todo():
    name = request.args.get('name')  # Access parameters standard way
    # TODO: Implement retrieval logic based on `name`
    return jsonify({"message": f"Todo for {name} retrieved."})

# GET request without request parameters
@app.route("/companies/<string:id>/lei", methods=["GET"])
async def get_lei(id: str):
    # TODO: Implement actual logic to retrieve LEI
    return jsonify({"lei": f"LEI for company {id}."})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```