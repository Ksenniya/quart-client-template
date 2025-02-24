import asyncio
import datetime

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION  # always use this constant
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token  # entity_service is not used since entity state is modified directly

app = Quart(__name__)
QuartSchema(app)

# Business logic: update the entity version attribute
def process_set_version(entity):
    entity["version"] = ENTITY_VERSION

# Business logic: initialize cyoda and store its result in the entity
async def process_init_cyoda(entity):
    # Initialize cyoda using the provided token and assign result to the entity
    entity["cyoda"] = init_cyoda(cyoda_token)

# Business logic: add a processing timestamp to the entity
def process_finalize(entity):
    entity["processed_at"] = datetime.datetime.utcnow().isoformat()

# Workflow orchestration: orchestrate calls to business logic functions
async def process_brands_log(entity):
    # Call business logic functions in sequence (workflow orchestration)
    entity = await process_entity(entity)
    process_set_version(entity)
    await process_init_cyoda(entity)
    process_finalize(entity)
    return entity

@app.route("/brands", methods=["POST"])
@validate_request()
async def brands_log_endpoint():
    entity = await request.get_json()
    processed_entity = await process_brands_log(entity)
    return jsonify(processed_entity)

if __name__ == "__main__":
    app.run()