import asyncio
import aiohttp
from dataclasses import dataclass

from quart import Quart, jsonify
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

@app.route('/brands/fetch', methods=['POST'])
@validate_request(FetchRequest)
async def fetch_brands(data: FetchRequest):
    # Fetch the external API data synchronously
    external_api_url = "https://api.practicesoftwaretesting.com/brands"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(external_api_url) as resp:
                if resp.status == 200:
                    external_data = await resp.json()
                else:
                    return jsonify({"error": f"Failed to fetch from external API, status {resp.status}"}), resp.status
        except Exception as e:
            return jsonify({"error": f"Exception occurred: {e}"}), 500

    # Use entity_service.add_item to store the fetched brands data.
    # The returned technical id can be used later to retrieve the stored entity.
    new_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,
        entity=external_data
    )
    return jsonify({"id": new_id})

@app.route('/brands', methods=['GET'])
async def get_brands():
    # Retrieve the list of stored brands via the external service.
    items = await entity_service.get_items(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,
    )
    if not items:
        return jsonify({"message": "No brand data available. Please trigger a fetch via POST /brands/fetch."}), 404
    return jsonify({"data": items})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)