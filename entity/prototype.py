import asyncio
import datetime
import aiohttp
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for brand data; using placeholder persistence.
brand_cache = {"data": []}

# Dataclass for POST /brands/update request
@dataclass
class BrandUpdateRequest:
    refresh: bool = False  # Optional flag to force update
    filter: str = ""       # Optional filter criteria

# Correct ordering workaround for POST requests:
# @app.route line must come first, then @validate_request.
@app.route('/brands/update', methods=['POST'])
@validate_request(BrandUpdateRequest)  # Workaround: placed after route decorator for POST requests.
async def update_brands(data: BrandUpdateRequest):
    # Create a mock job id and register a simple job state.
    job_id = "job_" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    entity_job = {job_id: {"status": "processing", "requestedAt": datetime.datetime.utcnow().isoformat()}}
    # TODO: In a full implementation, use a proper job queue/identifier mechanism.

    # Fire-and-forget processing task.
    asyncio.create_task(process_brands(entity_job))
    
    return jsonify({
        "message": "Brands data update initiated.",
        "job_id": job_id
    }), 200

async def process_brands(entity_job):
    # Process external API call, apply business logic and update local cache.
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://api.practicesoftwaretesting.com/brands") as response:
                if response.status != 200:
                    # TODO: Improve error handling and job status tracking in a robust solution.
                    job_key = list(entity_job.keys())[0]
                    entity_job[job_key]["status"] = "failed"
                    return

                data = await response.json()
                # TODO: Add additional filtering, transformation, or calculation as needed.
                brand_cache["data"] = data

                # Update the job status to completed.
                job_key = list(entity_job.keys())[0]
                entity_job[job_key]["status"] = "completed"
        except Exception as e:
            # TODO: Implement proper logging for exceptions.
            job_key = list(entity_job.keys())[0]
            entity_job[job_key]["status"] = "failed"
            return

# GET /brands endpoint does not require validation for query parameters.
@app.route('/brands', methods=['GET'])
async def get_brands():
    return jsonify({"data": brand_cache.get("data", [])}), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)