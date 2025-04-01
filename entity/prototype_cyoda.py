```python
from quart import Quart, request
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass
import logging
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service
import asyncio

app = Quart(__name__)
QuartSchema(app)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@dataclass
class Todo:
    task: str

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@app.route("/test", methods=["POST"])
@validate_request(Todo)  # Validation last for POST
async def create_todo(data: Todo):
    requested_at = "now"  # Placeholder for actual timestamp
    entity_data = data.__dict__

    try:
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="Todo",
            entity_version=ENTITY_VERSION,
            entity=entity_data
        )
        return {"job_id": job_id, "status": "processing"}, 202
    except Exception as e:
        logger.exception(e)
        return {"error": "Failed to create todo"}, 500

@app.route("/test", methods=["GET"])
@validate_querystring(Todo)  # Validation first for GET
async def get_todo():
    name = request.args.get('name')  # Accessing GET parameters

    try:
        todos = await entity_service.get_items(
            token=cyoda_token,
            entity_model="Todo",
            entity_version=ENTITY_VERSION
        )
        return {"todos": todos}, 200
    except Exception as e:
        logger.exception(e)
        return {"error": "Failed to retrieve todos"}, 500

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