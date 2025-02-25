#!/usr/bin/env python3
import asyncio
import datetime
from dataclasses import dataclass

import aiohttp
from quart import Quart, request, jsonify
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

# Background processing function to fetch external brand data and update the stored record
async def process_entity(job_id: str):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                'https://api.practicesoftwaretesting.com/brands',
                headers={'accept': 'application/json'}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Update the stored record with the retrieved data and mark as completed
                    update_payload = {
                        "technical_id": job_id,
                        "data": data,
                        "status": "completed",
                        "requestedAt": datetime.datetime.utcnow().isoformat()
                    }
                    await entity_service.update_item(
                        token=cyoda_token,
                        entity_model="brands",
                        entity_version=ENTITY_VERSION,
                        entity=update_payload,
                        meta={}
                    )
                else:
                    # In case of error, update the record status accordingly
                    error_payload = {
                        "technical_id": job_id,
                        "status": f"error_{resp.status}",
                        "requestedAt": datetime.datetime.utcnow().isoformat()
                    }
                    await entity_service.update_item(
                        token=cyoda_token,
                        entity_model="brands",
                        entity_version=ENTITY_VERSION,
                        entity=error_payload,
                        meta={}
                    )
                    print("Error: External API returned status", resp.status)
        except Exception as e:
            # Update record status to reflect exception if needed and log exception
            error_payload = {
                "technical_id": job_id,
                "status": "failed",
                "requestedAt": datetime.datetime.utcnow().isoformat()
            }
            await entity_service.update_item(
                token=cyoda_token,
                entity_model="brands",
                entity_version=ENTITY_VERSION,
                entity=error_payload,
                meta={}
            )
            print("Exception occurred during external API call:", e)

# Endpoint to trigger a brand data update
@app.route('/brands/update', methods=['POST'])
@validate_request(UpdateTrigger)
async def update_brands(data: UpdateTrigger):
    # Create a new record for asynchronous processing; the response will be retrieved later via GET /brands
    record = {
        "trigger": data.trigger,
        "status": "processing",
        "requestedAt": datetime.datetime.utcnow().isoformat()
    }
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,
        entity=record
    )
    # Fire and forget the processing task using the returned job_id as technical id
    asyncio.create_task(process_entity(job_id))
    return jsonify({
        "status": "success",
        "message": "Brand data update initiated",
        "job_id": job_id
    })

# Endpoint to retrieve brands data from external service
@app.route('/brands', methods=['GET'])
async def get_brands():
    # Retrieve all records for the "brands" entity
    items = await entity_service.get_items(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION
    )
    return jsonify(items)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)