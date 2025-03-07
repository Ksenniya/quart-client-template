import asyncio
import uuid
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

# Workflow function for "job" entity.
# This function is invoked asynchronously before persisting the job entity.
# It processes external data fetches and updates the entity state accordingly.
async def process_job(entity: dict):
    # Retrieve list of entities to fetch and filter parameters from the job data.
    fetch_entities = entity.pop("fetchEntities", ["pets", "orders", "users"])
    fetch_filter = entity.pop("fetchFilter", {})

    results = {}
    async with httpx.AsyncClient() as client:
        for fetched_entity in fetch_entities:
            try:
                if fetched_entity == "pets":
                    # Use filter status if provided, default to "available"
                    status = fetch_filter.get("status", "available")
                    url = "https://petstore.swagger.io/v2/pet/findByStatus"
                    params = {"status": status}
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    results["pets"] = response.json()
                    logger.info("Fetched %d pets.", len(results["pets"]))
                
                elif fetched_entity == "orders":
                    url = "https://petstore.swagger.io/v2/store/inventory"
                    response = await client.get(url)
                    response.raise_for_status()
                    # Placeholder for orders; replace with real order fetching when API details are clarified.
                    results["orders"] = response.json()
                    logger.info("Fetched orders inventory data.")
                
                elif fetched_entity == "users":
                    # No direct external API endpoint to fetch all users.
                    # Placeholder empty list for users.
                    results["users"] = []
                    logger.info("Users endpoint is not implemented; using placeholder.")
                else:
                    logger.info("Unknown entity: %s", fetched_entity)
            except Exception as e:
                logger.exception(e)
                results[fetched_entity] = {"error": f"Failed to fetch {fetched_entity}"}

    # Calculate summary metrics.
    summary = {
        "petCount": len(results.get("pets", [])) if isinstance(results.get("pets", []), list) else 0,
        "orderCount": len(results.get("orders", {})) if isinstance(results.get("orders", dict)) else 0,
        "userCount": len(results.get("users", []))
    }
    final_result = {
        "resultId": entity.get("technicalId", "unknown"),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": results,
        "summary": summary
    }
    # Modify the job entity state directly.
    entity["status"] = "completed"
    entity["result"] = final_result
    # Add additional workflow metadata.
    entity["workflowProcessed"] = True
    entity["processedAt"] = datetime.utcnow().isoformat() + "Z"
    # Note: Do not call entity_service.add/update/delete on the current entity!
    return entity

# Dataclass for POST request validation for /api/fetch-data.
@dataclass
class FetchDataRequest:
    entities: Optional[List[str]] = None
    filter: Optional[Dict[str, Any]] = None

@app.route("/api/fetch-data", methods=["POST"])
@validate_request(FetchDataRequest)  # Workaround: For POST endpoints, validate_request goes second.
async def fetch_data(data: FetchDataRequest):
    try:
        # Use validated data from request.
        fetch_entities = data.entities if data.entities is not None else ["pets", "orders", "users"]
        fetch_filter = data.filter if data.filter is not None else {}

        # Include the fetch info in the job_data to be used by the workflow.
        requested_at = datetime.utcnow().isoformat() + "Z"
        job_data = {
            "status": "processing",
            "requestedAt": requested_at,
            "fetchEntities": fetch_entities,
            "fetchFilter": fetch_filter
        }
        # Create a job record via the external service.
        # The workflow function process_job will be invoked asynchronously before persisting the entity.
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=job_data,  # the validated data object with additional fetch info
            workflow=process_job  # Workflow function applied to the entity asynchronously before persistence.
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