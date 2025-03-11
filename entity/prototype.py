import asyncio
import uuid
import logging
from datetime import datetime

import httpx
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

app = Quart(__name__)
QuartSchema(app)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# In-memory persistence for job data
jobs = {}

# External API URL
EXTERNAL_API_URL = "https://petstore.swagger.io/v2/swagger.json"

@dataclass
class FetchDataRequest:
    data_type: str
    filter: dict = None  # Optional filtering parameters

@dataclass
class ResultsQuery:
    data_id: str

async def process_entity(job_id: str, payload: dict):
    """
    Processes the external API request. Retrieves data from the external API,
    performs any business calculations and updates the job status with the result.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Call the external API to retrieve data.
            response = await client.get(EXTERNAL_API_URL)
            response.raise_for_status()
            external_data = response.json()
        
        logger.info("External API data retrieved successfully for job_id: %s", job_id)

        # TODO: Process the external_data using payload['data_type'] and payload['filter'] as needed.
        data_type = payload.get("data_type")
        processed_data = external_data  # Placeholder for actual processing logic
        if data_type:
            # TODO: Implement data filtering based on data_type and payload['filter'] if provided.
            processed_data = external_data  # Placeholder for filtered/processed data

        # Update the job with successful result.
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["processedAt"] = datetime.utcnow().isoformat()
        jobs[job_id]["data"] = processed_data
        logger.info("Job %s processed successfully", job_id)
    except Exception as e:
        logger.exception(e)
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)

# For POST requests, @app.route comes first, then @validate_request (workaround for current issue)
@app.route("/fetch_data", methods=["POST"])
@validate_request(FetchDataRequest)
async def fetch_data(data: FetchDataRequest):
    try:
        payload = data.__dict__
        if not payload or 'data_type' not in payload:
            return jsonify({"status": "error", "message": "Missing 'data_type' in request"}), 400

        # Create a unique data_id and record initial job data.
        data_id = str(uuid.uuid4())
        requested_at = datetime.utcnow().isoformat()
        jobs[data_id] = {
            "status": "processing",
            "requestedAt": requested_at,
            "data": None
        }
        logger.info("Started processing job %s at %s", data_id, requested_at)

        # Fire and forget the processing task.
        asyncio.create_task(process_entity(data_id, payload))
        
        return jsonify({
            "status": "success",
            "message": "Data has been fetched and processing has started.",
            "data_id": data_id
        }), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

# For GET requests, @validate_querystring must be placed first (workaround for current issue)
@validate_querystring(ResultsQuery)
@app.route("/results", methods=["GET"])
async def results():
    try:
        data_id = request.args.get("data_id")
        if not data_id:
            return jsonify({"status": "error", "message": "Missing 'data_id' parameter"}), 400

        job = jobs.get(data_id)
        if not job:
            return jsonify({"status": "error", "message": "Data not found"}), 404

        return jsonify({
            "status": "success",
            "data": job
        }), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)