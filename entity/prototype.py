import asyncio
import logging
import uuid
from datetime import datetime
from dataclasses import dataclass

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# In-memory cache for the inventory data and jobs
inventory_cache = None
job_store = {}

# TODO: In a production system, persistence would be handled using a database or external cache.
#       Here we mock persistence using in-memory dictionaries.

@dataclass
class InventoryFetchPayload:
    externalApiUrl: str = "https://petstore.swagger.io/v2/store/inventory"
    apiKey: str = "special-key"

async def process_entity(job_id: str, data: dict):
    """
    Background task to process the external API data.
    This function simulates processing and stores the result in an in-memory cache.
    """
    try:
        # Simulate processing delay
        await asyncio.sleep(1)
        # TODO: Include any data transformation or calculations here if needed.
        global inventory_cache
        inventory_cache = data
        job_store[job_id]["status"] = "completed"
        job_store[job_id]["completedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Job {job_id} completed processing.")
    except Exception as e:
        logger.exception(e)
        job_store[job_id]["status"] = "failed"

# For POST endpoints, the decorator order is: first @app.route, then @validate_request.
@app.route('/inventory/fetch', methods=['POST'])
@validate_request(InventoryFetchPayload)
async def fetch_inventory(data: InventoryFetchPayload):
    """
    POST endpoint to fetch inventory data from an external pet store API.
    """
    try:
        external_api_url = data.externalApiUrl
        api_key = data.apiKey

        headers = {"api_key": api_key}

        async with httpx.AsyncClient() as client:
            response = await client.get(external_api_url, headers=headers)
            response.raise_for_status()
            api_data = response.json()

        # Create a job to process the retrieved data
        job_id = str(uuid.uuid4())
        requested_at = datetime.utcnow().isoformat()
        job_store[job_id] = {"status": "processing", "requestedAt": requested_at}
        logger.info(f"Job {job_id} started at {requested_at}.")

        # Fire and forget the processing task.
        asyncio.create_task(process_entity(job_id, api_data))

        return jsonify({
            "status": "success",
            "jobId": job_id,
            "message": "Data fetch initiated. Please check /inventory for results after processing completes."
        })
    except httpx.HTTPError as e:
        logger.exception(e)
        return jsonify({
            "status": "error",
            "message": f"HTTP error occurred: {str(e)}"
        }), 500
    except Exception as e:
        logger.exception(e)
        return jsonify({
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}"
        }), 500

# GET endpoint does not require validation since no query parameters are expected.
@app.route('/inventory', methods=['GET'])
async def get_inventory():
    """
    GET endpoint to retrieve stored inventory results.
    """
    try:
        if inventory_cache is not None:
            return jsonify({
                "status": "success",
                "data": inventory_cache
            })
        else:
            return jsonify({
                "status": "error",
                "message": "No inventory data available. Please trigger /inventory/fetch first."
            }), 404
    except Exception as e:
        logger.exception(e)
        return jsonify({
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)