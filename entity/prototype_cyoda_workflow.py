#!/usr/bin/env python3
import asyncio
import datetime
from dataclasses import dataclass

import aiohttp
from quart import Quart, jsonify
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

# Workflow function applied to the "brands" entity asynchronously before persistence.
# This function modifies the entity state using asynchronous code.
async def process_brands(entity):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                'https://api.practicesoftwaretesting.com/brands',
                headers={'accept': 'application/json'}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Update the entity state with external data and mark as completed
                    entity["data"] = data
                    entity["status"] = "completed"
                else:
                    # Update the entity state to indicate an error based on the response status
                    entity["status"] = f"error_{resp.status}"
        except Exception as e:
            # Update the entity state to indicate failure
            entity["status"] = "failed"
    # Set the processing timestamp
    entity["requestedAt"] = datetime.datetime.utcnow().isoformat()
    return entity

# Endpoint to trigger a brand data update
@app.route('/brands/update', methods=['POST'])
@validate_request(UpdateTrigger)
async def update_brands(data: UpdateTrigger):
    # Create a new record with minimal data; it will be fully processed using the workflow function
    record = {
        "trigger": data.trigger,
        "status": "processing",
        "requestedAt": datetime.datetime.utcnow().isoformat()
    }
    # The process_brands workflow function will be applied asynchronously before persisting the record.
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=record,  # the validated data object
        workflow=process_brands  # Workflow function to modify the entity state
    )
    return jsonify({
        "status": "success",
        "message": "Brand data update initiated",
        "job_id": job_id
    })

# Endpoint to retrieve brands data from external service
@app.route('/brands', methods=['GET'])
async def get_brands():
    items = await entity_service.get_items(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION
    )
    return jsonify(items)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)