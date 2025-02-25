import asyncio
import aiohttp
import time
import uuid

from quart import Quart, request, jsonify
from quart_schema import QuartSchema

# Initialize the Quart app and QuartSchema
app = Quart(__name__)
QuartSchema(app)

# Global in-memory cache for brands data and job statuses
cached_brands = None
jobs = {}

@app.route('/brands/fetch', methods=['POST'])
async def fetch_brands():
    """
    POST endpoint to trigger the external API call and process the data.
    This endpoint starts a background task to fetch and process the brand data.
    """
    job_id = str(uuid.uuid4())
    requested_at = time.time()
    # Store initial job status
    jobs[job_id] = {"status": "processing", "requestedAt": requested_at}
    
    # Fire and forget: async processing task
    asyncio.create_task(process_entity(job_id))
    
    return jsonify({
        "message": "Brand fetch initiated.",
        "job_id": job_id
    })

@app.route('/brands', methods=['GET'])
async def get_brands():
    """
    GET endpoint to retrieve cached/processed brand data.
    """
    if cached_brands is None:
        # TODO: Consider implementing a more user-friendly mechanism to trigger a refresh or inform user of processing status.
        return jsonify({"message": "No brand data available. Please trigger a fetch via POST /brands/fetch."}), 404

    return jsonify({"data": cached_brands})

async def process_entity(job_id):
    """
    Background task to call the external API, process, and store the data.
    """
    global cached_brands
    external_api_url = "https://api.practicesoftwaretesting.com/brands"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(external_api_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # TODO: Insert any additional business logic, filtering or calculations here.
                    cached_brands = data  # Caching the processed results locally
                    jobs[job_id]["status"] = "completed"
                else:
                    jobs[job_id]["status"] = f"failed with status code {resp.status}"
        except Exception as e:
            jobs[job_id]["status"] = f"failed: {e}"
            # TODO: Add proper logging and error handling as needed.

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)