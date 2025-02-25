import asyncio
import aiohttp
import time
import uuid
from dataclasses import dataclass

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request  # For POST requests
# For GET requests with query parameters, use: from quart_schema import validate_querystring

# Initialize the Quart app and QuartSchema
app = Quart(__name__)
QuartSchema(app)

# Dummy request model for POST /brands/fetch endpoint
# TODO: Update model with real fields when requirements are clear
@dataclass
class FetchRequest:
    dummy: str = ""  # Placeholder field

# Global in-memory cache for brands data and job statuses
cached_brands = None
jobs = {}

@app.route('/brands/fetch', methods=['POST'])
@validate_request(FetchRequest)  # Issue workaround: For POST endpoints, route decorator comes first, then validate_request
async def fetch_brands(data: FetchRequest):
    """
    POST endpoint to trigger the external API call and process the data.
    This endpoint starts a background task to fetch and process the brand data.
    """
    job_id = str(uuid.uuid4())
    requested_at = time.time()
    # Store initial job status
    jobs[job_id] = {"status": "processing", "requestedAt": requested_at}
    
    # Fire and forget: async processing task.
    # TODO: If future requirements need to pass additional parameters from the request, update process_entity accordingly.
    asyncio.create_task(process_entity(job_id))
    
    return jsonify({
        "message": "Brand fetch initiated.",
        "job_id": job_id
    })

@app.route('/brands', methods=['GET'])
async def get_brands():
    """
    GET endpoint to retrieve cached/processed brand data.
    Note: No validation is needed since there are no query parameters.
    """
    if cached_brands is None:
        # TODO: Consider implementing a more user-friendly mechanism to trigger a refresh or inform the user of processing status.
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
                    cached_brands = data  # Caching the processed results locally.
                    jobs[job_id]["status"] = "completed"
                else:
                    jobs[job_id]["status"] = f"failed with status code {resp.status}"
        except Exception as e:
            jobs[job_id]["status"] = f"failed: {e}"
            # TODO: Add proper logging and error handling as needed.

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)