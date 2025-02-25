from common.grpc_client.grpc_client import grpc_stream
import asyncio
import aiohttp
from dataclasses import dataclass

from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)

@dataclass
class FetchRequest:
    dummy: str = ""  # Placeholder field

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

@app.route('/brands/fetch', methods=['POST'])
@validate_request(FetchRequest)
async def fetch_brands(data: FetchRequest):
    external_api_url = "https://api.practicesoftwaretesting.com/brands"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(external_api_url) as resp:
                if resp.status == 200:
                    external_data = await resp.json()
                else:
                    return jsonify({"error": f"Failed to fetch from external API, status {resp.status}"}), resp.status
    except aiohttp.ClientError as e:
        return jsonify({"error": f"Aiohttp client error occurred: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error occurred: {e}"}), 500

    # Validate that external_data is not empty
    if not external_data:
        return jsonify({"error": "No data received from external API"}), 500

    try:
        new_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=external_data,  # the fetched data from the external API
            )
    except Exception as e:
        return jsonify({"error": f"Error persisting entity: {e}"}), 500

    return jsonify({"id": new_id})

@app.route('/brands', methods=['GET'])
async def get_brands():
    try:
        items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        return jsonify({"error": f"Error retrieving brands: {e}"}), 500

    if not items:
        return jsonify({"message": "No brand data available. Please trigger a fetch via POST /brands/fetch."}), 404
    return jsonify({"data": items})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)