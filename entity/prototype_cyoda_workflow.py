#!/usr/bin/env python3
import asyncio
import datetime
import aiohttp
from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from app_init.app_init import cyoda_token, entity_service
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

# Application Startup: Initialize external services.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Dataclass for POST /brands/update request.
@dataclass
class BrandUpdateRequest:
    refresh: bool = False  # Optional flag to force update.
    filter: str = ""       # Optional filter criteria.

# Endpoint for updating brands. Minimal logic; asynchronous processing is moved to workflow functions.
@app.route('/brands/update', methods=['POST'])
@validate_request(BrandUpdateRequest)
async def update_brands(data: BrandUpdateRequest):
    # Create a unique job id.
    job_id = "job_" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    # Fire-and-forget task to process brands.
    asyncio.create_task(process_brands())
    return jsonify({
        "message": "Brands data update initiated.",
        "job_id": job_id
    }), 200

# Workflow function for 'brands' entity.
# This function is applied to each brand entity asynchronously before it is persisted.
async def brand_workflow(entity):
    try:
        # Add a processing timestamp.
        entity["processed_at"] = datetime.datetime.utcnow().isoformat()
        # Validate and ensure required keys are present.
        if "name" not in entity:
            entity["name"] = "Unknown"
        # Asynchronously fetch supplementary metadata from another entity_model.
        # Ensure that we are not interfering with operations on the current entity type.
        try:
            supplementary_metadata = await entity_service.get_items(
                token=cyoda_token,
                entity_model="brand_metadata",
                entity_version=ENTITY_VERSION,
            )
            if supplementary_metadata:
                # Attach the first metadata item as an example.
                entity["metadata"] = supplementary_metadata[0]
        except Exception:
            # In case of error fetching metadata, continue without failing.
            entity["metadata_error"] = "Failed to retrieve metadata"
        # Additional asynchronous processing can be implemented here if needed.
    except Exception as e:
        # Prevent workflow function from raising exceptions that might affect persistence.
        entity["workflow_error"] = str(e)
    return entity

# Asynchronous function to process brands data from external API.
async def process_brands():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://api.practicesoftwaretesting.com/brands") as response:
                if response.status != 200:
                    # Handle non-OK responses.
                    return
                brands_data = await response.json()
                if not isinstance(brands_data, list):
                    # Validate that the fetched data is a list.
                    return
                # Process each brand entry.
                for brand in brands_data:
                    # Use the workflow function to process the brand entity asynchronously before persistence.
                    await entity_service.add_item(
                        token=cyoda_token,
                        entity_model="brands",
                        entity_version=ENTITY_VERSION,
                        entity=brand,
                        workflow=brand_workflow
                    )
        except Exception:
            # Prevent exceptions from propagating.
            return

# Endpoint to retrieve persisted brands.
@app.route('/brands', methods=['GET'])
async def get_brands():
    try:
        items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,
        )
    except Exception:
        # Return empty list in case of error.
        items = []
    return jsonify({"data": items}), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)