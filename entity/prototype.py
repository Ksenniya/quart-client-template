```python
from quart import Quart, request
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass
import httpx
import asyncio
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for entities
entity_job = {}

@dataclass
class Todo:
    task: str

# Issue workaround: Always put validation first for GET requests and last for POST requests
@app.route("/test", methods=["POST"])
@validate_request(Todo)  # This should be last in POST
async def create_todo(data: Todo):
    requested_at = asyncio.get_event_loop().time()
    entity_job[data.task] = {"status": "processing", "requestedAt": requested_at}
    # Fire and forget the processing task
    await asyncio.create_task(process_entity(entity_job[data.task], data.__dict__))
    return {"message": "Todo created", "task": data.task}, 201

@app.route("/test", methods=["GET"])
@validate_querystring(Todo)  # This should be first in GET
async def get_todo():
    name = request.args.get('task')  # Use standard approach to access parameters values for GET requests
    if name in entity_job:
        return entity_job[name], 200
    return {"message": "Todo not found"}, 404

@app.route("/companies/<string:id>/lei", methods=["GET"])
async def get_companies_lei(id: str):
    # TODO: Implement the logic to retrieve LEI from a real API
    return {"company_id": id, "lei": "mocked_lei_value"}, 200

async def process_entity(entity, data):
    # TODO: Implement the processing logic, potentially calling an external API
    pass

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```