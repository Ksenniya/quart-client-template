```python
from quart import Quart, request
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass
import httpx
import asyncio
import logging

app = Quart(__name__)
QuartSchema(app)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Placeholder for local cache
entity_job = {}

@dataclass
class Todo:
    task: str

# Workaround issue: validation first for GET, last for POST
@app.route("/test", methods=["POST"])
@validate_request(Todo)  # Validation last for POST
async def create_todo(data: Todo):
    requested_at = "now"  # Placeholder for actual timestamp
    job_id = len(entity_job) + 1  # Simple increment for job ID
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}
    
    # TODO: Add actual processing logic
    await asyncio.create_task(process_entity(entity_job, data.__dict__))
    
    return {"job_id": job_id, "status": "processing"}, 202

@app.route("/test", methods=["GET"])
@validate_querystring(Todo)  # Validation first for GET
async def get_todo():
    name = request.args.get('name')  # Accessing GET parameters
    # TODO: Retrieve todo from a local cache or a real data source
    return {"name": name}, 200

@app.route("/companies/<string:id>/lei", methods=["GET"])
async def get_company_lei(id: str):
    # TODO: Implement the logic to fetch LEI from an external API
    return {"id": id, "lei": "mocked_lei_value"}, 200

async def process_entity(entity_job, data):
    # TODO: Implement processing logic
    pass

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```