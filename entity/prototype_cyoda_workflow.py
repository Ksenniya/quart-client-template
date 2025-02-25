#!/usr/bin/env python3
"""
Prototype implementation for a Quart API that fetches and displays brand data.
This version replaces all in‐memory cache interactions with calls to the external
entity_service. Data is stored via add_item and later retrieved via get_items.
"""

import asyncio
import datetime
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request  # noqa: E402
import aiohttp

from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service
from common.config.config import ENTITY_VERSION

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Data class for POST /brands request validation.
@dataclass
class BrandRequest:
    refresh: bool = False

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Workflow function applied to the brand entity before persistence.
async def process_brands(entity_data):
    # Example workflow: add a processed timestamp and flag to the entity data.
    entity_data["processed_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    entity_data["is_processed"] = True
    # You can add additional processing logic here.
    return entity_data

# POST /brands endpoint.
@app.route("/brands", methods=["POST"])
@validate_request(BrandRequest)
async def post_brands(data: BrandRequest):
    """
    POST /brands
    Retrieves brand data from an external API and stores it via the external entity_service.
    If refresh is False, it first checks if data already exists.
    """
    refresh = data.refresh

    if not refresh:
        # Check if brand data already exists in the external service.
        existing_data = await entity_service.get_items(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,
        )
        if existing_data:
            return jsonify({
                "success": True,
                "message": "Brand data already processed and available.",
                "data": existing_data,
            })

    # External API endpoint for brand data.
    external_api_url = "https://api.practicesoftwaretesting.com/brands"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(external_api_url) as resp:
                external_data = await resp.json()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    # Store the data asynchronously using the external entity_service and apply the workflow.
    # The workflow function process_brands will be applied to the entity asynchronously before persistence.
    job_id = await entity_service.add_item(
         token=cyoda_token,
         entity_model="brands",
         entity_version=ENTITY_VERSION,  # always use this constant
         entity=external_data,  # the validated data object
         workflow=process_brands  # Workflow function applied to the entity
    )

    return jsonify({
         "success": True,
         "message": "Processing initiated.",
         "jobId": job_id
    })

# GET /brands endpoint.
@app.route("/brands", methods=["GET"])
async def get_brands():
    """
    GET /brands
    Returns the processed/stored brand data retrieved via the external entity_service.
    """
    brands_data = await entity_service.get_items(
         token=cyoda_token,
         entity_model="brands",
         entity_version=ENTITY_VERSION,
    )
    if not brands_data:
         return jsonify({"success": False, "error": "No brand data available. Initiate processing via POST."}), 404

    return jsonify(brands_data)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)