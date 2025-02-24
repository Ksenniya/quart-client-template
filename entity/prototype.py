import asyncio
import aiohttp
import uuid
import datetime
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

app = Quart(__name__)
QuartSchema(app)

# In-memory caches for processed brand data and job status
brands_cache = []  # Global variable to store processed brand data
jobs = {}          # Global dictionary to track job statuses

async def process_entity(job, data):
    # Simulate processing delay
    await asyncio.sleep(1)  # TODO: Replace with actual processing logic if needed

    global brands_cache
    # TODO: Add any additional transformations or business logic here
    processed_data = data

    # Update the cache with processed data
    brands_cache = processed_data

    # Update job status
    job["status"] = "completed"
    job["completedAt"] = datetime.datetime.utcnow().isoformat()

@app.route('/brands', methods=['POST'])
async def create_brands():
    global jobs
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()

    # Initialize job status
    job = {"status": "processing", "requestedAt": requested_at}
    jobs[job_id] = job

    # Optionally, read filter criteria or other parameters from the request body
    request_data = await request.get_json() or {}
    # TODO: Process request_data if specific filters or parameters are required

    # Retrieve data from the external API
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://api.practicesoftwaretesting.com/brands", 
            headers={"accept": "application/json"}
        ) as resp:
            if resp.status != 200:
                return jsonify({"error": "Failed to fetch external data"}), 500
            external_data = await resp.json()

    # Fire and forget the processing task.
    # For this prototype, we await the task completion to return processed data.
    task = asyncio.create_task(process_entity(job, external_data))
    await task

    # Return the processed brand data
    return jsonify(brands_cache), 200

@app.route('/brands', methods=['GET'])
async def get_brands():
    if not brands_cache:
        return jsonify({"error": "No data available. Please trigger a POST to /brands"}), 404
    return jsonify(brands_cache), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)