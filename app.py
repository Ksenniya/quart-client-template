from common.grpc_client.grpc_client import grpc_stream
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
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

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