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

@dataclass
class FetchRequest:
    refresh: bool = False  # Optional flag to force refresh; primitive type as required

@app.route('/api/brands/fetch', methods=['POST'])
@validate_request(FetchRequest)
async def fetch_brands(data: FetchRequest):
    # Generate a simple job id (TODO: Consider using uuid in production)
    requested_at = datetime.datetime.utcnow().isoformat()
    job_id = f"job_{requested_at}"
    # Using a temporary local job tracker (not persisted in external service)
    entity_job = {}
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}
    
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(entity_job, job_id))
    
    return jsonify({
        "status": "success",
        "message": "Brand data fetch initiated.",
        "jobId": job_id
    })

async def process_entity(entity_job, job_id):
    """
    Asynchronous task to fetch data from the external API, process it,
    and store the results via the external entity_service.
    """
    external_api_url = 'https://api.practicesoftwaretesting.com/brands'
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(external_api_url, headers={"accept": "application/json"}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # For each brand item, add it via the external service.
                    for item in data:
                        await entity_service.add_item(
                            token=cyoda_token,
                            entity_model="brands",
                            entity_version=ENTITY_VERSION,
                            entity=item
                        )
                    entity_job[job_id]["status"] = "completed"
                else:
                    entity_job[job_id]["status"] = "failed"
        except Exception as e:
            # Log error as needed.
            entity_job[job_id]["status"] = "failed"

@app.route('/api/brands', methods=['GET'])
async def get_brands():
    # Retrieve all brand items via entity_service.
    data = await entity_service.get_items(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,
    )
    return jsonify({"data": data})

@app.route('/api/brands/<string:brand_id>', methods=['GET'])
async def get_brand(brand_id: str):
    # Retrieve a single brand item by id via entity_service.
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