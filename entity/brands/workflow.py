import asyncio
import datetime

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION  # always use this constant
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)

# Business logic: process the entity with a minimal delay
async def process_entity(entity):
    # Simulate asynchronous processing (extend with real business logic if needed)
    await asyncio.sleep(0.1)
    return entity

# Business logic: add metadata to the current entity
def process_set_metadata(entity):
    entity["processed"] = True
    entity["processed_at"] = datetime.datetime.utcnow().isoformat()
    return entity

# Business logic: log the brand processing using a separate entity model
async def process_log_brand(entity):
    try:
        log_entry = {
            "brand_id": entity.get("id"),
            "logged_at": datetime.datetime.utcnow().isoformat(),
            "info": "Brand processing initiated"
        }
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="brands_log",
            entity_version=ENTITY_VERSION,
            entity=log_entry,
            workflow=process_entity  # Using generic processing for the log entry
        )
    except Exception as e:
        # In production, consider logging the exception appropriately
        pass
    return entity

@app.route("/brands", methods=["POST"])
@validate_request()
async def brands_endpoint():
    entity = await request.get_json()
    processed_entity = await process_brands(entity)
    return jsonify(processed_entity)

if __name__ == "__main__":
    app.run()