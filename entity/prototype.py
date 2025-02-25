import asyncio
import datetime
import aiohttp
from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# In-memory storage for brands data
brands_cache = {}

@dataclass
class FetchRequest:
    refresh: bool = False  # Optional flag to force refresh; primitive type as required

@app.route('/api/brands/fetch', methods=['POST'])
@validate_request(FetchRequest)  # For POST, validation goes after route decorator (workaround for quart-schema issue)
async def fetch_brands(data: FetchRequest):
    # The 'data' parameter contains the validated request body
    requested_at = datetime.datetime.utcnow().isoformat()
    # Generate a simple job id (TODO: Consider using uuid in production)
    job_id = f"job_{requested_at}"
    entity_job = {}
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}
    
    # Fire and forget the processing task.
    # TODO: Enhance error handling and job tracking as necessary.
    asyncio.create_task(process_entity(entity_job, job_id))
    
    return jsonify({
        "status": "success",
        "message": "Brand data fetch initiated.",
        "jobId": job_id
    })

async def process_entity(entity_job, job_id):
    """
    Asynchronous task to fetch data from the external API, process it,
    and store the results in the in-memory cache.
    
    TODO: Incorporate additional business logic and error handling as required.
    """
    external_api_url = 'https://api.practicesoftwaretesting.com/brands'
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(external_api_url, headers={"accept": "application/json"}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # TODO: Apply any necessary transformations or calculations.
                    brands_cache['brands'] = data
                    entity_job[job_id]["status"] = "completed"
                else:
                    entity_job[job_id]["status"] = "failed"
                    brands_cache['brands'] = []
        except Exception as e:
            # TODO: Log the exception and handle errors appropriately.
            entity_job[job_id]["status"] = "failed"
            brands_cache['brands'] = []

@app.route('/api/brands', methods=['GET'])
async def get_brands():
    # No validation decorator needed for GET without query parameters
    data = brands_cache.get('brands', [])
    return jsonify({"data": data})

@app.route('/api/brands/<string:brand_id>', methods=['GET'])
async def get_brand(brand_id: str):
    # No validation decorator needed for GET without query parameters
    brands = brands_cache.get('brands', [])
    # Filter the brand with a matching id.
    brand = next((b for b in brands if b.get("id") == brand_id), None)
    if brand:
        return jsonify(brand)
    return jsonify({"error": "Brand not found"}), 404

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)