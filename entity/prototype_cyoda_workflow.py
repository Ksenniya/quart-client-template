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
QuartSchema(app)  # Initialize QuartSchema

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Request schema for the fetch endpoint; additional parameters could be added here
@dataclass
class FetchRequest:
    refresh: bool = False  # Optional flag to force refresh; primitive type as required

# Workflow function for processing an individual brand entity
async def process_brand(entity):
    # Example: add a processed timestamp to the brand entity
    entity["processedAt"] = datetime.datetime.utcnow().isoformat()
    # You may add additional async tasks here such as fetching supplementary info
    return entity

# Workflow function for processing the fetch job entity.
# This function fetches external brand data and adds each brand entity using its workflow.
async def process_brands_fetch(entity):
    external_api_url = 'https://api.practicesoftwaretesting.com/brands'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(external_api_url, headers={"accept": "application/json"}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # For each brand item, add it via entity_service with its workflow function.
                    for item in data:
                        await entity_service.add_item(
                            token=cyoda_token,
                            entity_model="brands",
                            entity_version=ENTITY_VERSION,
                            entity=item,
                            workflow=process_brand  # Apply async processing before persistence.
                        )
                    # Update the job entity state with success details.
                    entity["status"] = "completed"
                    entity["completedAt"] = datetime.datetime.utcnow().isoformat()
                    entity["processedCount"] = len(data)
                else:
                    entity["status"] = "failed"
                    entity["error"] = f"HTTP error: {resp.status}"
    except Exception as e:
        entity["status"] = "failed"
        entity["error"] = str(e)
    return entity

# Endpoint to initiate fetching brands.
# Instead of running a fire-and-forget task in the controller, we delegate processing to a workflow.
@app.route('/api/brands/fetch', methods=['POST'])
@validate_request(FetchRequest)
async def fetch_brands(data: FetchRequest):
    # Generate a job id based on the current UTC time
    requested_at = datetime.datetime.utcnow().isoformat()
    job_id = f"job_{requested_at}"
    # Prepare a job entity for the fetch task.
    job_entity = {
        "jobId": job_id,
        "requestedAt": requested_at,
        "status": "processing"
    }
    # Add the job entity using entity_service.
    # The workflow function process_brands_fetch will perform the external API call
    # and handle adding each brand entity with its own workflow (process_brand).
    await entity_service.add_item(
        token=cyoda_token,
        entity_model="brands_fetch_job",
        entity_version=ENTITY_VERSION,
        entity=job_entity,
        workflow=process_brands_fetch
    )
    
    return jsonify({
        "status": "success",
        "message": "Brand data fetch initiated.",
        "jobId": job_id
    })

# Endpoint to retrieve all brand items.
@app.route('/api/brands', methods=['GET'])
async def get_brands():
    data = await entity_service.get_items(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,
    )
    return jsonify({"data": data})

# Endpoint to retrieve a single brand item by its id.
@app.route('/api/brands/<string:brand_id>', methods=['GET'])
async def get_brand(brand_id: str):
    brand = await entity_service.get_item(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,
        technical_id=brand_id
    )
    if brand:
        return jsonify(brand)
    return jsonify({"error": "Brand not found"}), 404

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)