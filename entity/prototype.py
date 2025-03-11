import asyncio
import uuid
import logging
from datetime import datetime
from dataclasses import dataclass, field

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request  # For GET endpoints, use validate_querystring if needed

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for job persistence
jobs_cache = {}

@dataclass
class FetchDataRequest:
    resource: str
    options: dict = field(default_factory=dict)

# For POST endpoints, route decorator comes first, then validate_request decorator.
@app.route('/api/fetch-data', methods=["POST"])
@validate_request(FetchDataRequest)  # Workaround: for POST, validation decorator is placed after route decorator.
async def fetch_data(data: FetchDataRequest):
    try:
        resource = data.resource
        options = data.options

        job_id = str(uuid.uuid4())
        requested_at = datetime.utcnow().isoformat()
        jobs_cache[job_id] = {"status": "processing", "requestedAt": requested_at, "data": None}

        # Fire and forget the processing task.
        asyncio.create_task(process_entity(job_id, resource, options))

        return jsonify({
            "job_id": job_id,
            "message": "Data retrieval initiated and processing in progress."
        }), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal Server Error"}), 500

# GET endpoint: no validation required as there is no request body or query parameters.
@app.route('/api/results/<job_id>', methods=["GET"])
async def get_results(job_id: str):
    job = jobs_cache.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({
        "job_id": job_id,
        "status": job["status"],
        "data": job["data"]
    })

async def process_entity(job_id: str, resource: str, options: dict):
    try:
        logger.info("Processing job %s for resource: %s", job_id, resource)
        result = None
        if resource == "pet":
            # Retrieve pets by status from external Petstore API.
            statuses = options.get("status", ["available"])
            params = {"status": statuses}
            async with httpx.AsyncClient() as client:
                # The external API endpoint for finding pets by status.
                response = await client.get("https://petstore.swagger.io/v2/pet/findByStatus", params=params)
                response.raise_for_status()
                result = response.json()
        elif resource == "store":
            # TODO: Implement external API call for store resource.
            logger.info("Processing for store resource is not yet implemented.")
            result = {"message": "Store resource processing not implemented", "data": None}
        elif resource == "user":
            # TODO: Implement external API call for user resource.
            logger.info("Processing for user resource is not yet implemented.")
            result = {"message": "User resource processing not implemented", "data": None}
        else:
            result = {"error": f"Unsupported resource '{resource}'."}
        
        # TODO: Perform any specific calculations here if required.
        
        jobs_cache[job_id]["data"] = result
        jobs_cache[job_id]["status"] = "completed"
        logger.info("Job %s completed successfully.", job_id)
    except Exception as e:
        logger.exception(e)
        jobs_cache[job_id]["status"] = "failed"
        jobs_cache[job_id]["data"] = {"error": str(e)}

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)