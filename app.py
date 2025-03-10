from common.grpc_client.grpc_client import grpc_stream
import asyncio
import datetime
import logging
import httpx

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass

# External service functions and configurations
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Constant for the entity model name used across external service calls
ENTITY_MODEL = "entity/prototype"

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

# Data models for request validation
@dataclass
class FetchDataRequest:
    external_api: str  # Expected to be "petstore"

@dataclass
class ResultsQuery:
    fetch_id: str

# POST /fetch-data endpoint to initiate data fetching process.
@app.route('/fetch-data', methods=['POST'])
@validate_request(FetchDataRequest)
async def fetch_data(data: FetchDataRequest):
    """
    POST /fetch-data:
    Initiates the process to fetch external data and perform processing using the workflow function.
    All asynchronous processing is done in the workflow before persisting the entity.
    """
    if data.external_api.lower() != "petstore":
        return jsonify({"error": "Unsupported external_api value. Expected 'petstore'."}), 400

    # Create initial job entity with processing status.
    requested_at = datetime.datetime.utcnow().isoformat()
    job_entity = {
        "status": "processing",
        "requestedAt": requested_at
    }
    try:
        # Call external service to add the job entity.
        # The workflow function process_prototype is applied asynchronously before persistence.
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=job_entity,
            )
    except Exception as e:
        logger.exception("Failed to add job entity: %s", e)
        return jsonify({"error": "Failed to initiate job"}), 500

    return jsonify({
        "fetch_id": job_id,
        "status": "success",
        "message": "Data fetching initiated successfully."
    })

# GET /results endpoint to retrieve results of a previously initiated job.
@validate_querystring(ResultsQuery)
@app.route('/results', methods=['GET'])
async def get_results():
    """
    GET /results:
    Retrieves the processed entity for a previously initiated job.
    """
    fetch_id = request.args.get('fetch_id')
    if not fetch_id:
        return jsonify({"error": "Missing fetch_id"}), 400
    try:
        result = await entity_service.get_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            technical_id=fetch_id
        )
    except Exception as e:
        logger.exception("Error retrieving entity for fetch_id %s: %s", fetch_id, e)
        return jsonify({"error": "Error retrieving job result"}), 500

    if result is None:
        return jsonify({"error": "Invalid fetch_id or job not found"}), 400

    return jsonify({
        "fetch_id": fetch_id,
        "status": result.get("status", "unknown"),
        "data": result.get("data", {})
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)