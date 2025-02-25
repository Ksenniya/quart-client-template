#!/usr/bin/env python3
"""
Prototype implementation for a Quart API that fetches and displays brand data.
This is a working prototype using in-memory caching and async processing with aiohttp.ClientSession.
TODO: Replace any mocks/placeholders (e.g. in-memory cache) with persistent solutions in a production environment.
"""

import asyncio
import datetime
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request  # noqa: E402
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# In-memory cache for storing processed brand data
cache = {}

# In-memory job store for tracking processing tasks (mock)
jobs = {}

# Data class for POST /brands request validation.
# Note: Only primitives are allowed.
@dataclass
class BrandRequest:
    refresh: bool = False

async def process_entity(job, data):
    """
    Simulate processing of external data.
    TODO: Implement any necessary business logic or calculations before storing the data.
    """
    # Simulate processing delay
    await asyncio.sleep(1)
    # In this prototype, we simply store the retrieved data in the cache.
    cache['brands'] = data
    # Mark the job as completed.
    job["status"] = "completed"
    job["completedAt"] = datetime.datetime.utcnow().isoformat()

# For POST endpoints, the route decorator goes first, then the validation decorator.
# This is a workaround for an issue in the quart-schema library.
@app.route("/brands", methods=["POST"])
@validate_request(BrandRequest)
async def post_brands(data: BrandRequest):
    """
    POST /brands
    Retrieves brand data from an external API and processes the data asynchronously.
    """
    refresh = data.refresh

    # If not refreshing and data exists in cache, we can immediately return the cached data.
    if not refresh and cache.get("brands"):
        return jsonify({
            "success": True,
            "message": "Brand data already processed and available.",
            "data": cache["brands"]
        })

    # Generate a unique job ID based on current timestamp.
    job_id = "job_" + datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    job_entry = {
        "status": "processing",
        "requestedAt": datetime.datetime.utcnow().isoformat()
    }
    jobs[job_id] = job_entry

    # External API endpoint for brand data.
    external_api_url = "https://api.practicesoftwaretesting.com/brands"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(external_api_url) as resp:
                external_data = await resp.json()
    except Exception as e:
        # Mark the job as failed and return error response.
        job_entry["status"] = "failed"
        return jsonify({"success": False, "error": str(e)}), 500

    # Fire and forget the processing task.
    # TODO: Consider handling task results more robustly in a production solution.
    asyncio.create_task(process_entity(job_entry, external_data))

    return jsonify({
        "success": True,
        "message": "Processing initiated.",
        "jobId": job_id
    })

# GET endpoint does not require validation since no query parameters are used.
@app.route("/brands", methods=["GET"])
async def get_brands():
    """
    GET /brands
    Returns the processed/stored brand data.
    """
    brands_data = cache.get("brands")
    if brands_data is None:
        # TODO: In a complete implementation, handle waiting or triggering process for data retrieval.
        return jsonify({"success": False, "error": "No brand data available. Initiate processing via POST."}), 404

    return jsonify(brands_data)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)