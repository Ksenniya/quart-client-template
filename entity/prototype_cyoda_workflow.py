#!/usr/bin/env python3
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request
import asyncio
import aiohttp
import datetime
from dataclasses import dataclass

from common.config.config import ENTITY_VERSION  # always use this constant
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)

# Dataclass for filtering brands; kept minimal on purpose
@dataclass
class BrandFilter:
    filter: str = ""  # Optional filter criteria; using only primitives

# Fire-and-forget function example: logs supplementary data by adding a new entity of a different model.
async def log_brand_processing(brand_data):
    # Example: Add a log entry to the "brands_log" entity_model.
    log_entry = {
        "brand_id": brand_data.get("id"),
        "logged_at": datetime.datetime.utcnow().isoformat(),
        "info": "Brand processing initiated"
    }
    # We assume entity_service.add_item for "brands_log" works without risk of recursion
    await entity_service.add_item(
        token=cyoda_token,
        entity_model="brands_log",
        entity_version=ENTITY_VERSION,
        entity=log_entry,
        workflow=process_entity  # Reuse a generic processing if needed.
    )

# Generic processing function, available for any workflow that does not require brand-specific logic.
async def process_entity(data):
    await asyncio.sleep(0.1)  # Minimal delay; adjust as needed
    return data

# Workflow function for 'brands' entities.
# This function is applied asynchronously on the entity before persistence.
async def process_brands(entity_data):
    # Example: add processing metadata directly to the entity.
    entity_data['processed'] = True
    entity_data['processed_at'] = datetime.datetime.utcnow().isoformat()

    # Initiate any asynchronous fire-and-forget tasks (e.g. logging or supplemental processing)
    asyncio.create_task(log_brand_processing(entity_data))
    
    # Additional business logic can be placed here without cluttering the controller.
    # e.g., entity_data['new_attribute'] = compute_value(entity_data)

    return entity_data

# Startup: initialize external components before serving requests.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# POST endpoint for creating brands.
# The controller logic is minimized: it simply fetches external data and hands off processing to the workflow.
@app.route('/brands', methods=['POST'])
@validate_request(BrandFilter)
async def create_brands(data: BrandFilter):
    # Retrieve data from an external API.
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://api.practicesoftwaretesting.com/brands",
            headers={"accept": "application/json"}
        ) as resp:
            if resp.status != 200:
                return jsonify({"error": "Failed to fetch external data"}), 500
            external_data = await resp.json()

    # Submit the external data to the entity service.
    # The workflow function process_brands will be invoked asynchronously before persistence.
    item_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,
        entity=external_data,
        workflow=process_brands  # Offload additional async tasks & state modifications here.
    )

    # Return the created item id.
    return jsonify({"id": item_id}), 200

# GET endpoint to retrieve brands data from the external service.
@app.route('/brands', methods=['GET'])
async def get_brands():
    items = await entity_service.get_items(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,
    )
    if not items:
        return jsonify({"error": "No data available. Please trigger a POST to /brands"}), 404
    return jsonify(items), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)