#!/usr/bin/env python3
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request
import asyncio
import aiohttp
import uuid
import datetime
from dataclasses import dataclass

from common.config.config import ENTITY_VERSION  # always use this constant
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)

# Removed in‐memory caches and job trackers; using external service instead

@dataclass
class BrandFilter:
    filter: str = ""  # Optional filter criteria; using only primitives

# Generic processing function (if needed elsewhere)
async def process_entity(data):
    await asyncio.sleep(1)
    return data

# Workflow function for 'brands' entity; can modify the data prior to persistence
async def process_brands(data):
    # Simulate processing delay and update entity state, e.g. add a processing timestamp
    await asyncio.sleep(1)
    # Example of modifying the data; adjust as needed for business logic
    data['processed'] = True
    data['processed_at'] = datetime.datetime.now().isoformat()
    return data

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# For POST endpoints, route decorator comes first and validate_request comes second (workaround for quart-schema issue)
@app.route('/brands', methods=['POST'])
@validate_request(BrandFilter)
async def create_brands(data: BrandFilter):
    # Access validated data from the request body; currently not being used directly in processing
    request_data = data

    # Retrieve data from the external API
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://api.practicesoftwaretesting.com/brands",
            headers={"accept": "application/json"}
        ) as resp:
            if resp.status != 200:
                return jsonify({"error": "Failed to fetch external data"}), 500
            external_data = await resp.json()

    # Process the external data (simulate delay and apply any needed business logic)
    processed_data = await process_entity(external_data)

    # Add the processed data to the external service via entity_service using the workflow function for brands
    item_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,
        entity=processed_data,
        workflow=process_brands  # Workflow function applied asynchronously before persistence
    )

    # Return only the id in the response (retrieval of the item is via a separate endpoint)
    return jsonify({"id": item_id}), 200

# GET endpoint to retrieve brands data from the external service
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