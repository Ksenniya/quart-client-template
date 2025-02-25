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
    try:
        await init_cyoda(cyoda_token)
    except Exception as e:
        # Log the error and prevent startup if initialization fails.
        print(f"Initialization error: {str(e)}")
        raise

# Asynchronous function to fetch supplementary data.
async def fetch_supplementary_data():
    supplementary_url = "https://api.practicesoftwaretesting.com/brands/supplementary"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(supplementary_url, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    # Log failure and return empty dict if non-200 response.
                    print(f"Supplementary data fetch failed with status {resp.status}")
                    return {}
    except Exception as e:
        # Log the exception and return empty dict to avoid breaking the workflow.
        print(f"Supplementary data fetch exception: {str(e)}")
        return {}

# Fire-and-forget async task for logging processing details.
async def log_processing(entity_model, entity_id):
    try:
        # Simulate asynchronous logging (this could be replaced with real logging).
        await asyncio.sleep(0)
        print(f"Processed entity for model '{entity_model}' with id '{entity_id}'")
    except Exception as e:
        # Capture any exceptions in logging to prevent it from affecting the workflow.
        print(f"Logging exception: {str(e)}")

# Workflow function applied to the brand entity before persistence.
async def process_brands(entity_data):
    try:
        # Add a processed timestamp and flag to the entity data.
        entity_data["processed_at"] = datetime.datetime.utcnow().isoformat() + "Z"
        entity_data["is_processed"] = True

        # Fetch supplementary data asynchronously and update the entity.
        supplementary = await fetch_supplementary_data()
        if supplementary:
            entity_data["supplementary_info"] = supplementary

        # Fire-and-forget asynchronous logging.
        entity_id = entity_data.get("id", "unknown")
        asyncio.create_task(log_processing("brands", entity_id))

        # Additional asynchronous tasks (if any) can be added here.
    except Exception as e:
        # If any error occurs during processing, log it.
        print(f"Workflow processing error: {str(e)}")
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
        try:
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
        except Exception as e:
            # Log and continue to fetch fresh data if checking fails.
            print(f"Error retrieving existing data: {str(e)}")

    # External API endpoint for brand data.
    external_api_url = "https://api.practicesoftwaretesting.com/brands"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(external_api_url, timeout=10) as resp:
                if resp.status == 200:
                    external_data = await resp.json()
                else:
                    return jsonify({"success": False, "error": f"External API responded with status {resp.status}"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    try:
        # Store the data asynchronously using the external entity_service and apply the workflow.
        # The workflow function process_brands will be invoked asynchronously to transform
        # the entity before its persistence.
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=external_data,  # the validated data object
            workflow=process_brands  # Workflow function applied to the entity
        )
    except Exception as e:
        return jsonify({"success": False, "error": f"Error storing data: {str(e)}"}), 500

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
    try:
        brands_data = await entity_service.get_items(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        return jsonify({"success": False, "error": f"Error retrieving brand data: {str(e)}"}), 500

    if not brands_data:
         return jsonify({"success": False, "error": "No brand data available. Initiate processing via POST."}), 404

    return jsonify(brands_data)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)