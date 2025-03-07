import asyncio
import uuid
import logging
from datetime import datetime
from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for entity jobs.
JOB_CACHE = {}

# Base URL for the external Petstore API.
PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

@app.route("/api/fetch-data", methods=["POST"])
async def fetch_data():
    try:
        payload = await request.get_json()
        entities = payload.get("entities", ["pets", "orders", "users"])
        filter_params = payload.get("filter", {})

        job_id = str(uuid.uuid4())
        requested_at = datetime.utcnow().isoformat() + "Z"
        JOB_CACHE[job_id] = {"status": "processing", "requestedAt": requested_at}

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
                    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
                    params = {"status": status}
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    results["pets"] = response.json()
                    logger.info("Fetched %d pets.", len(results["pets"]))
                
                elif entity == "orders":
                    # Get the inventory as a placeholder for orders.
                    url = f"{PETSTORE_BASE_URL}/store/inventory"
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
    JOB_CACHE[job_id].update({"status": "completed", "result": final_result})
    logger.info("Job %s completed.", job_id)

@app.route("/api/results/<job_id>", methods=["GET"])
async def get_results(job_id):
    try:
        job = JOB_CACHE.get(job_id)
        if not job:
            return jsonify({"error": "Result not found."}), 404
        if job.get("status") != "completed":
            return jsonify({"status": "processing",
                            "message": "Data is still being processed."}), 202
        return jsonify(job.get("result")), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve results."}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)