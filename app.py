from common.grpc_client.grpc_client import grpc_stream
import asyncio
import datetime
from dataclasses import dataclass

import aiohttp
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from common.repository.cyoda.cyoda_init import init_cyoda
from common.config.config import ENTITY_VERSION
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)

# Dataclass for POST request trigger
@dataclass
class UpdateTrigger:
    trigger: str  # e.g., "manual"

# Startup initialization of cyoda
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

# Workflow function for supplementary operations on other entity models.
# This function demonstrates how to add secondary data if required.
# Note: Do not call entity_service.add_item/update_item on the current entity's model to avoid recursion.
async def process_secondary_data(entity):
    # For demonstration, if a secondary attribute is needed, create a supplementary record.
    supplementary_record = {
        "reference": entity.get("trigger", "unknown"),
        "createdAt": datetime.datetime.utcnow().isoformat(),
        "info": "Supplementary data associated with the brand update"
    }
    try:
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="supplementary",
            entity_version=ENTITY_VERSION,
            entity=supplementary_record,
            workflow=None  # No workflow for supplementary data or use a different workflow if needed.
        )
    except Exception as e:
        # Log the error or pass since it is supplementary.
        print("Error adding supplementary data:", e)
    return entity

# Endpoint to trigger a brand data update
@app.route('/brands/update', methods=['POST'])
@validate_request(UpdateTrigger)
async def update_brands(data: UpdateTrigger):
    # Create a new record with minimal data. It will be processed using the workflow function.
    record = {
        "trigger": data.trigger,
        "status": "processing",
        "requestedAt": datetime.datetime.utcnow().isoformat()
    }
    # The process_brands workflow function will be applied asynchronously before persisting the record.
    # Additional secondary processing can be chained inside process_brands or via separate workflow functions.
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=record,  # the validated data object
        )
    # Optionally trigger supplementary processing on another entity.
    # This is fire-and-forget and the errors inside process_secondary_data will not affect the main flow.
    asyncio.create_task(process_secondary_data(record))
    return jsonify({
        "status": "success",
        "message": "Brand data update initiated",
        "job_id": job_id
    })

# Endpoint to retrieve brands data
@app.route('/brands', methods=['GET'])
async def get_brands():
    try:
        items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve items",
            "error": str(e)
        }), 500
    return jsonify(items)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)