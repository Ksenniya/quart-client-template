#!/usr/bin/env python3
import asyncio
import aiohttp
from dataclasses import dataclass

from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)

@dataclass
class FetchRequest:
    dummy: str = ""  # Placeholder field

# Supplementary asynchronous task for additional processing (fire and forget)
# This task stores an audit record in a different entity_model.
async def store_audit_record(audit_data):
    # Simulate additional asynchronous processing before storing the audit record.
    # Note: Using a different entity_model ("brands_audit") to avoid recursion.
    await entity_service.add_item(
        token=cyoda_token,
        entity_model="brands_audit",
        entity_version=ENTITY_VERSION,
        entity=audit_data,
        workflow=lambda x: x  # No additional workflow required for audit records.
    )

# Workflow function applied to the entity asynchronously before persistence.
# Any heavy processing and fire-and-forget tasks can be moved inside this function.
async def process_brands(entity):
    # Example modification: mark the entity as processed.
    if isinstance(entity, dict):
        entity["processed"] = True

        # Create audit data from the entity (only a subset or the full data as needed)
        audit_record = {
            "source": "external_api",
            "entity_id": entity.get("id"),
            "status": "processed"
        }
        # Fire and forget: store the audit record in a different entity model.
        asyncio.create_task(store_audit_record(audit_record))
    return entity

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@app.route('/brands/fetch', methods=['POST'])
@validate_request(FetchRequest)
async def fetch_brands(data: FetchRequest):
    # Fetch the external API data asynchronously
    external_api_url = "https://api.practicesoftwaretesting.com/brands"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(external_api_url) as resp:
                if resp.status == 200:
                    external_data = await resp.json()
                else:
                    return jsonify({"error": f"Failed to fetch from external API, status {resp.status}"}), resp.status
        except Exception as e:
            return jsonify({"error": f"Exception occurred: {e}"}), 500

    # The workflow function process_brands now encapsulates additional logic,
    # relieving the endpoint from heavy processing and fire-and-forget tasks.
    new_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=external_data,  # the fetched data from the external API
        workflow=process_brands  # Workflow function applied to the entity before persistence
    )
    return jsonify({"id": new_id})

@app.route('/brands', methods=['GET'])
async def get_brands():
    # Retrieve the list of stored brands via the external service.
    items = await entity_service.get_items(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,
    )
    if not items:
        return jsonify({"message": "No brand data available. Please trigger a fetch via POST /brands/fetch."}), 404
    return jsonify({"data": items})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)