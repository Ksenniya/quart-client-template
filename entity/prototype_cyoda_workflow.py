import asyncio
import logging
import datetime
from dataclasses import dataclass
from typing import Optional

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
import httpx

from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Data class for POST request validation
@dataclass
class DataSourceParameters:
    optional_parameter1: Optional[str] = None
    optional_parameter2: Optional[str] = None

# Workflow function applied to the entity before persistence.
# It fetches external data, processes it, and updates the entity accordingly.
async def process_data_sources(entity):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://jsonplaceholder.typicode.com/posts/1")
            response.raise_for_status()
            external_data = response.json()
        # Business logic: combine title and body as processed result
        processed_result = f"Processed: {external_data.get('title', '')} & {external_data.get('body', '')}"
        # Update the entity's data with external data and processed result
        entity["data"] = {
            "title": external_data.get("title"),
            "body": external_data.get("body"),
            "processedResult": processed_result,
            "status": "done"
        }
        logger.info("Entity processed successfully in workflow")
    except Exception as e:
        # In case of error, update the entity with failed status
        entity["data"] = {"status": "failed"}
        logger.exception(e)
    return entity

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# POST endpoint for data_sources. Validation is done via Quart Schema.
@app.route('/data_sources', methods=['POST'])
@validate_request(DataSourceParameters)
async def data_sources(data: DataSourceParameters):
    try:
        requested_at = datetime.datetime.utcnow().isoformat()
        # Prepare the entity data for creation
        job_data = {
            "status": "processing",
            "requestedAt": requested_at
        }
        # Create a new job entity via the external entity_service.
        # The workflow function process_data_sources will be applied to the entity before persistence.
        technical_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="data_sources",
            entity_version=ENTITY_VERSION,
            entity=job_data,
            workflow=process_data_sources
        )
        return jsonify({
            "status": "success",
            "message": "Processing initiated",
            "job_id": technical_id
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

# GET endpoint for retrieving processed results.
@app.route('/results', methods=['GET'])
async def results():
    try:
        # Retrieve all items for the data_sources entity from the external entity_service.
        items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="data_sources",
            entity_version=ENTITY_VERSION
        )
        return jsonify({
            "status": "success",
            "results": items
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)