from common.grpc_client.grpc_client import grpc_stream
import asyncio
import uuid
import logging
from datetime import datetime

import httpx
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# External API URL
EXTERNAL_API_URL = "https://petstore.swagger.io/v2/swagger.json"

# Startup initialization for external cyoda service
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

@dataclass
class FetchDataRequest:
    data_type: str
    filter: dict = None  # Optional filtering parameters

@dataclass
class ResultsQuery:
    data_id: str

@app.route("/fetch_data", methods=["POST"])
@validate_request(FetchDataRequest)
async def fetch_data(data: FetchDataRequest):
    try:
        payload = data.__dict__
        if not payload or "data_type" not in payload:
            return jsonify({"status": "error", "message": "Missing 'data_type' in request"}), 400

        # Create a unique job id and record initial job data.
        job_id = str(uuid.uuid4())
        requested_at = datetime.utcnow().isoformat()
        # Include the payload in the initial entity for use in the workflow.
        initial_job_data = {
            "status": "processing",
            "requestedAt": requested_at,
            "data": None,
            "payload": payload
        }
        # Save the job entity. The workflow function process_job will be invoked
        # asynchronously to update the entity state before it gets persisted.
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            entity=initial_job_data,
            )
        logger.info("Job %s started processing at %s", job_id, requested_at)
        return jsonify({
            "status": "success",
            "message": "Data has been fetched and is being processed.",
            "data_id": job_id
        }), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

@validate_querystring(ResultsQuery)
@app.route("/results", methods=["GET"])
async def results():
    try:
        job_id = request.args.get("data_id")
        if not job_id:
            return jsonify({"status": "error", "message": "Missing 'data_id' parameter"}), 400

        job = await entity_service.get_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
        if not job:
            return jsonify({"status": "error", "message": "Data not found"}), 404

        return jsonify({
            "status": "success",
            "data": job
        }), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)