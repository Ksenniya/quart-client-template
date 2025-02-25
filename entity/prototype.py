import asyncio
import datetime
import aiohttp
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# In-memory storage for brands data
brands_cache = {}

@app.route('/api/brands/fetch', methods=['POST'])
async def fetch_brands():
    """
    Triggers fetching of brand data from the external API.
    This endpoint fires off an asynchronous task to process the data.
    """
    requested_at = datetime.datetime.utcnow().isoformat()
    # Generate a simple job id (placeholder, consider using uuid in production)
    job_id = f"job_{requested_at}"
    entity_job = {}
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}
    
    # Fire and forget the processing task.
    # TODO: Consider handling exceptions and job tracking with a more robust system.
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
                    # TODO: Apply specific transformations or calculations as needed.
                    brands_cache['brands'] = data
                    entity_job[job_id]["status"] = "completed"
                else:
                    # In case of an error from the external API, record failure.
                    entity_job[job_id]["status"] = "failed"
                    brands_cache['brands'] = []
        except Exception as e:
            # TODO: Log the exception and handle errors appropriately.
            entity_job[job_id]["status"] = "failed"
            brands_cache['brands'] = []

@app.route('/api/brands', methods=['GET'])
async def get_brands():
    """
    Retrieves the stored brand data from the in-memory persistence.
    """
    data = brands_cache.get('brands', [])
    return jsonify({"data": data})

@app.route('/api/brands/<string:brand_id>', methods=['GET'])
async def get_brand(brand_id: str):
    """
    Retrieves detailed information for a specific brand identified by brand_id.
    """
    brands = brands_cache.get('brands', [])
    # Filter the brand with a matching id.
    brand = next((b for b in brands if b.get("id") == brand_id), None)
    if brand:
        return jsonify(brand)
    return jsonify({"error": "Brand not found"}), 404

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)