import asyncio
import uuid
import datetime
import logging

from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for storing job results
entity_job = {}

# Mapping for external API endpoints
EXTERNAL_API_BASE = "https://petstore.swagger.io/v2"

# TODO: Add additional endpoint mappings and their parameter formatting logic as requirements evolve.
async def process_entity(job_id: str, endpoint: str, params: dict):
    try:
        url = ""
        if endpoint == "findPetsByStatus":
            # Extract status parameter, default to 'available' if not provided
            status = params.get("status", "available")
            url = f"{EXTERNAL_API_BASE}/pet/findByStatus?status={status}"
        else:
            # TODO: Handle other endpoint types accordingly.
            raise ValueError(f"Unsupported endpoint: {endpoint}")

        logger.info(f"Processing job {job_id}: Calling external API at {url}")
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        # Simulate additional business logic or calculations if needed
        # TODO: Add any business logic/calculation steps as required.

        # Update job result in the in-memory cache
        entity_job[job_id].update({
            "status": "Completed",
            "data": data,
            "completedAt": datetime.datetime.utcnow().isoformat()
        })
        logger.info(f"Job {job_id} completed successfully.")
    except Exception as e:
        logger.exception(e)
        entity_job[job_id].update({
            "status": "Failed",
            "error": str(e)
        })

@app.route('/fetch-data', methods=['POST'])
async def fetch_data():
    try:
        req_data = await request.get_json()
        endpoint = req_data.get("endpoint")
        params = req_data.get("params", {})

        if not endpoint:
            return jsonify({"error": "Missing 'endpoint' in request body"}), 400

        job_id = str(uuid.uuid4())
        requested_at = datetime.datetime.utcnow().isoformat()

        # Store initial job status in the in-memory cache
        entity_job[job_id] = {
            "status": "Processing",
            "requestedAt": requested_at,
            "data": None
        }
        logger.info(f"Received fetch-data request. Job ID: {job_id}")

        # Fire and forget the processing task
        asyncio.create_task(process_entity(job_id, endpoint, params))

        return jsonify({
            "job_id": job_id,
            "status": "Processing",
            "message": "Your request is being processed"
        }), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/results/<job_id>', methods=['GET'])
async def get_results(job_id):
    try:
        job = entity_job.get(job_id)
        if not job:
            return jsonify({"error": "Job ID not found"}), 404
        return jsonify({
            "job_id": job_id,
            "status": job.get("status"),
            "data": job.get("data")
        }), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)