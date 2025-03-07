from common.grpc_client.grpc_client import grpc_stream
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request  # Workaround: For POST requests, route decorator comes first.
import httpx

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

# Dataclass for POST request validation for /api/fetch-data.
@dataclass
class FetchDataRequest:
    entities: Optional[List[str]] = None
    filter: Optional[Dict[str, Any]] = None

@app.route("/api/fetch-data", methods=["POST"])
@validate_request(FetchDataRequest)  # Workaround: For POST endpoints, validate_request goes second.
async def fetch_data(data: FetchDataRequest):
    try:
        # Obtain fetch parameters from request.
        fetch_entities = data.entities if data.entities is not None else ["pets", "orders", "users"]
        fetch_filter = data.filter if data.filter is not None else {}

        requested_at = datetime.utcnow().isoformat() + "Z"
        # Include fetch parameters in the job data for use in the workflow.
        job_data = {
            "status": "processing",
            "requestedAt": requested_at,
            "fetchEntities": fetch_entities,
            "fetchFilter": fetch_filter
        }
        # Create a job record via the external service.
        # The workflow function process_job will be applied asynchronously before persisting the entity.
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=job_data,  # job data including fetch parameters
            )

        return jsonify({
            "resultId": job_id,
            "message": "Data fetch initiated successfully.",
            "fetchedEntities": fetch_entities
        }), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to initiate data fetch."}), 500

@app.route("/api/results/<job_id>", methods=["GET"])
async def get_results(job_id):
    try:
        job = await entity_service.get_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
        if not job:
            return jsonify({"error": "Result not found."}), 404
        if job.get("status") != "completed":
            return jsonify({
                "status": "processing",
                "message": "Data is still being processed."
            }), 202
        return jsonify(job.get("result")), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve results."}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)