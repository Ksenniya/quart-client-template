#!/usr/bin/env python3
import asyncio
import datetime
import aiohttp
from dataclasses import dataclass
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from app_init.app_init import cyoda_token, entity_service
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Dataclass for POST /brands/update request
@dataclass
class BrandUpdateRequest:
    refresh: bool = False  # Optional flag to force update
    filter: str = ""       # Optional filter criteria

# Endpoint remains clean; business and async logic moved to workflow function.
@app.route('/brands/update', methods=['POST'])
@validate_request(BrandUpdateRequest)
async def update_brands(data: BrandUpdateRequest):
    job_id = "job_" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    # Fetch and add brands with workflow processing; no extra logic in the controller.
    asyncio.create_task(process_brands())
    return jsonify({
        "message": "Brands data update initiated.",
        "job_id": job_id
    }), 200

# Workflow function for 'brands' entity.
# This function is applied to each brand entity before persistence.
async def brand_workflow(entity):
    # Add a timestamp to mark processing time.
    entity["processed_at"] = datetime.datetime.utcnow().isoformat()
    # Example of asynchronous supplementary processing:
    # Fetch supplementary metadata from a different entity_model.
    try:
        metadata_list = await entity_service.get_items(
            token=cyoda_token,
            entity_model="brand_metadata",
            entity_version=ENTITY_VERSION,
        )
        if metadata_list:
            # For example, attach first metadata item.
            entity["metadata"] = metadata_list[0]
    except Exception:
        pass
    # Additional asynchronous operations can be placed here.
    return entity

async def process_brands():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://api.practicesoftwaretesting.com/brands") as response:
                if response.status != 200:
                    return
                brands_data = await response.json()
                for brand in brands_data:
                    # Instead of having asynchronous logic here,
                    # the workflow function will handle any additional operations.
                    await entity_service.add_item(
                        token=cyoda_token,
                        entity_model="brands",
                        entity_version=ENTITY_VERSION,
                        entity=brand,
                        workflow=brand_workflow
                    )
        except Exception:
            return

@app.route('/brands', methods=['GET'])
async def get_brands():
    items = await entity_service.get_items(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,
    )
    return jsonify({"data": items}), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)