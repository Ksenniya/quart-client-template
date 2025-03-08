import asyncio
import uuid
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from quart import Quart, request, jsonify
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
        entities = data.entities if data.entities is not None else ["pets", "orders", "users"]
        filter_params = data.filter if data.filter is not None else {}

        requested_at = datetime.utcnow().isoformat() + "Z"
        # Create a job record via the external service.
        job_data = {"status": "processing", "requestedAt": requested_at}
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            entity=job_data
        )

        # Fire and forget the processing task.
        asyncio.create_task(process_entities(job_id, entities, filter_params))
        return jsonify({
            "resultId": job_id,
            "message": "Data fetch initiated successfully.",
            "fetchedEntities": entities
        }), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to initiate data fetch."}), 500

async def process_entities(job_id, entities, filter_params):
    results = {}
    async with httpx.AsyncClient() as client:
        for entity in entities:
            try:
                if entity == "pets":
                    # Use filter status if provided, default to "available"
                    status = filter_params.get("status", "available")
                    url = f"https://petstore.swagger.io/v2/pet/findByStatus"
                    params = {"status": status}
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    results["pets"] = response.json()
                    logger.info("Fetched %d pets.", len(results["pets"]))
                
                elif entity == "orders":
                    # Get the inventory as a placeholder for orders.
                    url = f"https://petstore.swagger.io/v2/store/inventory"
                    response = await client.get(url)
                    response.raise_for_status()
                    # TODO: Replace with real order fetching when endpoint is clarified.
                    results["orders"] = response.json()
                    logger.info("Fetched orders inventory data.")
                
                elif entity == "users":
                    # No direct external API endpoint to fetch all users.
                    # TODO: Implement real user fetching logic or use another data source.
                    results["users"] = []  # Placeholder empty list for users.
                    logger.info("Users endpoint is not implemented; using placeholder.")
                else:
                    logger.info("Unknown entity: %s", entity)
            except Exception as e:
                logger.exception(e)
                results[entity] = {"error": f"Failed to fetch {entity}"}

    # Calculate summary metrics.
    summary = {
        "petCount": len(results.get("pets", [])) if isinstance(results.get("pets", []), list) else 0,
        "orderCount": len(results.get("orders", {})) if isinstance(results.get("orders", dict)) else 0,
        "userCount": len(results.get("users", []))
    }
    final_result = {
        "resultId": job_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": results,
        "summary": summary
    }
    # Update the job record via the external service.
    update_data = {"status": "completed", "result": final_result}
    try:
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            entity=update_data,
            technical_id=job_id,
            meta={}
        )
        logger.info("Job %s completed.", job_id)
    except Exception as e:
        logger.exception(e)

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