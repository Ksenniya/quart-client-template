import asyncio
import uuid
import logging
from datetime import datetime
from dataclasses import dataclass, field

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@dataclass
class FetchDataRequest:
    resource: str
    options: dict = field(default_factory=dict)

@app.route('/api/fetch-data', methods=["POST"])
@validate_request(FetchDataRequest)
async def fetch_data(data: FetchDataRequest):
    try:
        resource = data.resource
        options = data.options

        requested_at = datetime.utcnow().isoformat()
        job_data = {"status": "processing", "requestedAt": requested_at, "data": None}

        # Add job via external entity service and get a technical id (job_id)
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            entity=job_data
        )

        # Fire and forget the processing task.
        asyncio.create_task(process_entity(job_id, resource, options))

        return jsonify({
            "job_id": job_id,
            "message": "Data retrieval initiated and processing in progress."
        }), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/api/results/<job_id>', methods=["GET"])
async def get_results(job_id: str):
    try:
        job = await entity_service.get_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
        if not job:
            return jsonify({"error": "Job not found"}), 404
        return jsonify({
            "job_id": job_id,
            "status": job.get("status"),
            "data": job.get("data")
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal Server Error"}), 500

async def process_entity(job_id: str, resource: str, options: dict):
    try:
        logger.info("Processing job %s for resource: %s", job_id, resource)
        result = None
        if resource == "pet":
            statuses = options.get("status", ["available"])
            params = {"status": statuses}
            async with httpx.AsyncClient() as client:
                response = await client.get("https://petstore.swagger.io/v2/pet/findByStatus", params=params)
                response.raise_for_status()
                result = response.json()
        elif resource == "store":
            logger.info("Processing for store resource is not yet implemented.")
            result = {"message": "Store resource processing not implemented", "data": None}
        elif resource == "user":
            logger.info("Processing for user resource is not yet implemented.")
            result = {"message": "User resource processing not implemented", "data": None}
        else:
            result = {"error": f"Unsupported resource '{resource}'."}

        update_data = {"data": result, "status": "completed"}
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            entity=update_data,
            technical_id=job_id,
            meta={}
        )
        logger.info("Job %s completed successfully.", job_id)
    except Exception as e:
        logger.exception(e)
        update_data = {"data": {"error": str(e)}, "status": "failed"}
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            entity=update_data,
            technical_id=job_id,
            meta={}
        )

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)