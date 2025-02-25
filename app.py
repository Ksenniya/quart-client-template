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
QuartSchema(app)  # Initialize QuartSchema

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

# Request schema for fetch endpoint.
@dataclass
class FetchRequest:
    refresh: bool = False  # Indicates if a refresh is forced

# Endpoint to trigger the asynchronous fetching of brand data.
# Instead of handling async tasks in the controller, the workflow function is used.
@app.route('/api/brands/fetch', methods=['POST'])
@validate_request(FetchRequest)
async def fetch_brands(fetch_data: FetchRequest):
    # Generate a unique job identifier using the current UTC timestamp.
    requested_at = datetime.datetime.utcnow().isoformat()
    job_id = f"job_{requested_at}"
    # Initial job entity state.
    job_entity = {
        "jobId": job_id,
        "requestedAt": requested_at,
        "status": "processing"
    }
    # Add the job entity. The workflow function process_brands_fetch will be invoked
    # before persistence, handling the external API call and processing each brand.
    try:
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="brands_fetch_job",
            entity_version=ENTITY_VERSION,
            entity=job_entity,
            )
    except Exception as e:
        # If adding the job entity fails, return an error response.
        return jsonify({"status": "failed", "message": str(e)}), 500

    # Return the job id immediately.
    return jsonify({
        "status": "success",
        "message": "Brand data fetch initiated.",
        "jobId": job_id
    })

# Endpoint to retrieve all persisted brand items.
@app.route('/api/brands', methods=['GET'])
async def get_brands():
    try:
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"data": data})

# Endpoint to retrieve a single brand by its identifier.
@app.route('/api/brands/<string:brand_id>', methods=['GET'])
async def get_brand(brand_id: str):
    try:
        brand = await entity_service.get_item(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,
            technical_id=brand_id
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if brand:
        return jsonify(brand)
    return jsonify({"error": "Brand not found"}), 404

if __name__ == '__main__':
    # Run the Quart application with debugging enabled.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)