import asyncio
import uuid
import datetime
import logging
import httpx

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Use "job" as the external entity model name for job processing.
# Data class for validating fetch_data requests.
from dataclasses import dataclass

@dataclass
class FetchDataRequest:
    endpoint: str
    params: dict

EXTERNAL_API_BASE = "https://petstore.swagger.io/v2"

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Process the entity by calling an external API and then updating the job status via the external service.
async def process_entity(job_id: str, endpoint: str, params: dict):
    try:
        url = ""
        if endpoint == "findPetsByStatus":
            status = params.get("status", "available")
            url = f"{EXTERNAL_API_BASE}/pet/findByStatus?status={status}"
        else:
            raise ValueError(f"Unsupported endpoint: {endpoint}")

        logger.info(f"Processing job {job_id}: Calling external API at {url}")
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        update_data = {
            "status": "Completed",
            "data": data,
            "completedAt": datetime.datetime.utcnow().isoformat()
        }
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            entity=update_data,
            technical_id=job_id,
            meta={}
        )
        logger.info(f"Job {job_id} completed successfully.")
    except Exception as e:
        logger.exception(e)
        update_data = {
            "status": "Failed",
            "error": str(e)
        }
        try:
            await entity_service.update_item(
                token=cyoda_token,
                entity_model="job",
                entity_version=ENTITY_VERSION,
                entity=update_data,
                technical_id=job_id,
                meta={}
            )
        except Exception as inner_e:
            logger.exception(inner_e)

@app.route('/fetch-data', methods=['POST'])
@validate_request(FetchDataRequest)  # Workaround: For POST requests, route decorator comes first, then validation.
async def fetch_data(data: FetchDataRequest):
    try:
        endpoint = data.endpoint
        params = data.params

        if not endpoint:
            return jsonify({"error": "Missing 'endpoint' in request body"}), 400

        requested_at = datetime.datetime.utcnow().isoformat()
        job_data = {
            "status": "Processing",
            "requestedAt": requested_at,
            "data": None,
            "endpoint": endpoint,
            "params": params
        }

        # Add new job via external service
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            entity=job_data
        )
        logger.info(f"Received fetch-data request. Job ID: {job_id}")

        # Fire and forget the processing task.
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
        job = await entity_service.get_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
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