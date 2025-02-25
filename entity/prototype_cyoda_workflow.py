#!/usr/bin/env python3
import asyncio
import datetime
import aiohttp
from dataclasses import dataclass
from quart import Quart, request, jsonify
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

@app.route('/brands/update', methods=['POST'])
@validate_request(BrandUpdateRequest)
async def update_brands(data: BrandUpdateRequest):
    # Create a mock job id and register a simple job state.
    job_id = "job_" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    # Fire-and-forget processing task.
    asyncio.create_task(process_brands())
    return jsonify({
        "message": "Brands data update initiated.",
        "job_id": job_id
    }), 200

# Workflow function for 'brands' entity.
async def brand_workflow(entity):
    # Example workflow: add a flag to indicate processing.
    entity["workflow_processed"] = True
    # Additional processing logic can be added here.
    return entity

async def process_brands():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://api.practicesoftwaretesting.com/brands") as response:
                if response.status != 200:
                    # In a real implementation, log the error or update job status.
                    return
                brands_data = await response.json()
                # Process each brand item using the external persistence service.
                for brand in brands_data:
                    # Add each brand item with the workflow function applied before persistence.
                    await entity_service.add_item(
                        token=cyoda_token,
                        entity_model="brands",
                        entity_version=ENTITY_VERSION,
                        entity=brand,
                        workflow=brand_workflow
                    )
        except Exception as e:
            # Log exception as needed in a real implementation.
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