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

# Dataclass for validating brand filter data from requests
@dataclass
class BrandFilter:
    filter: str = ""  # Optional filter criteria; using only primitives

# Generic processing function for simple transformations
async def process_entity(data):
    # Minimal delay; extend processing logic if needed
    await asyncio.sleep(0.1)
    return data

# Fire-and-forget function to log brand processing; adds a supplementary log entity
async def log_brand_processing(brand_data):
    try:
        log_entry = {
            "brand_id": brand_data.get("id"),
            "logged_at": datetime.datetime.utcnow().isoformat(),
            "info": "Brand processing initiated"
        }
        # Add a log entry using a different entity_model to avoid recursion
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="brands_log",
            entity_version=ENTITY_VERSION,
            entity=log_entry,
            workflow=process_entity  # Use generic processing for log entry
        )
    except Exception as e:
        # Handle exceptions in logging to prevent unhandled errors in fire-and-forget tasks
        # In production, consider logging this error appropriately
        pass

# Workflow function for 'brands' entity
# This function is applied asynchronously to the entity before it is persisted
async def process_brands(entity_data):
    try:
        # Add processing metadata directly to the entity
        entity_data['processed'] = True
        entity_data['processed_at'] = datetime.datetime.utcnow().isoformat()
        # Modify or add any additional attributes here as needed
        # Initiate any asynchronous supplementary tasks (fire-and-forget)
        asyncio.create_task(log_brand_processing(entity_data))
    except Exception as e:
        # In production, handle/log exception appropriately
        pass
    return entity_data

@app.before_serving
async def startup():
    # Initialize cyoda service before handling any requests
    await init_cyoda(cyoda_token)

# POST endpoint to create/update brands
# This endpoint minimizes controller logic by offloading processing to workflow functions
@app.route('/brands', methods=['POST'])
@validate_request(BrandFilter)
async def create_brands(data: BrandFilter):
    try:
        # Retrieve brand data from an external API
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.practicesoftwaretesting.com/brands",
                headers={"accept": "application/json"}
            ) as resp:
                if resp.status != 200:
                    return jsonify({"error": "Failed to fetch external data"}), 500
                external_data = await resp.json()
    except Exception as e:
        # Return error if external API call fails
        return jsonify({"error": "Exception occurred while fetching external data"}), 500

    try:
        # Submit the external data to the entity service.
        # The workflow function process_brands will modify the entity asynchronously before persistence.
        item_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,
            entity=external_data,
            workflow=process_brands  # Offload additional async tasks & state modifications here
        )
    except Exception as e:
        # Handle errors during the add_item operation
        return jsonify({"error": "Exception occurred while persisting data"}), 500

    # Return the created item id
    return jsonify({"id": item_id}), 200

# GET endpoint to retrieve brands data from the external service
@app.route('/brands', methods=['GET'])
async def get_brands():
    try:
        items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,
        )
        if not items:
            return jsonify({"error": "No data available. Please trigger a POST to /brands"}), 404
        return jsonify(items), 200
    except Exception as e:
        # Handle retrieval errors
        return jsonify({"error": "Exception occurred while retrieving data"}), 500

if __name__ == '__main__':
    # Start the Quart server with appropriate configurations
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)