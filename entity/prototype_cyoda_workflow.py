#!/usr/bin/env python3
import asyncio
import aiohttp
from dataclasses import dataclass

from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)

@dataclass
class FetchRequest:
    dummy: str = ""  # Placeholder field

# Supplementary asynchronous task to store an audit record.
# This function uses a different entity_model to avoid interfering with the main entity.
async def store_audit_record(audit_data):
    try:
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="brands_audit",  # Use a different entity_model to avoid recursion.
            entity_version=ENTITY_VERSION,
            entity=audit_data,
            workflow=lambda x: x  # No additional workflow processing for audit records.
        )
    except Exception as e:
        # Log the error or handle it appropriately; for simplicity, we print the error.
        print(f"Error storing audit record: {e}")

# Workflow function applied to the entity asynchronously before persistence.
# Any heavy processing or asynchronous fire-and-forget tasks can be moved here.
async def process_brands(entity):
    try:
        # Verify that the entity is a dictionary
        if isinstance(entity, dict):
            # Example modification: mark the entity as processed.
            entity["processed"] = True

            # Create an audit record from the entity.
            audit_record = {
                "source": "external_api",
                "entity_id": entity.get("id", None),
                "status": "processed"
            }
            # Fire and forget: store the audit record asynchronously.
            asyncio.create_task(store_audit_record(audit_record))
        return entity
    except Exception as e:
        # In case of any processing error, log it and return the entity unmodified.
        print(f"Error in process_brands workflow: {e}")
        return entity

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@app.route('/brands/fetch', methods=['POST'])
@validate_request(FetchRequest)
async def fetch_brands(data: FetchRequest):
    external_api_url = "https://api.practicesoftwaretesting.com/brands"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(external_api_url) as resp:
                if resp.status == 200:
                    external_data = await resp.json()
                else:
                    return jsonify({"error": f"Failed to fetch from external API, status {resp.status}"}), resp.status
    except aiohttp.ClientError as e:
        return jsonify({"error": f"Aiohttp client error occurred: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error occurred: {e}"}), 500

    # Validate that external_data is not empty
    if not external_data:
        return jsonify({"error": "No data received from external API"}), 500

    try:
        new_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=external_data,  # the fetched data from the external API
            workflow=process_brands  # Workflow function applied to the entity before persistence
        )
    except Exception as e:
        return jsonify({"error": f"Error persisting entity: {e}"}), 500

    return jsonify({"id": new_id})

@app.route('/brands', methods=['GET'])
async def get_brands():
    try:
        items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        return jsonify({"error": f"Error retrieving brands: {e}"}), 500

    if not items:
        return jsonify({"message": "No brand data available. Please trigger a fetch via POST /brands/fetch."}), 404
    return jsonify({"data": items})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)