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

# Remove local in‑memory caches; now using external entity_service

# Data class for POST request validation
@dataclass
class DataSourceParameters:
    optional_parameter1: Optional[str] = None
    optional_parameter2: Optional[str] = None

# This function processes the external data and updates the corresponding job entity
async def process_entity(technical_id, external_data):
    try:
        # Business logic: combine title and body as processed result
        processed_result = f"Processed: {external_data.get('title', '')} & {external_data.get('body', '')}"
        # Prepare updated information for the entity: include external data and processing result
        update_data = {
            "id": external_data.get("id"),
            "data": {
                "title": external_data.get("title"),
                "body": external_data.get("body"),
                "processedResult": processed_result,
                "status": "done"
            }
        }
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="data_sources",
            entity_version=ENTITY_VERSION,
            entity=update_data,
            technical_id=technical_id,
            meta={}
        )
        logger.info(f"Processed entity job {technical_id}")
    except Exception as e:
        logger.exception(e)
        # In case of error, update the entity with failed status
        try:
            fail_data = {
                "data": {
                    "status": "failed"
                }
            }
            await entity_service.update_item(
                token=cyoda_token,
                entity_model="data_sources",
                entity_version=ENTITY_VERSION,
                entity=fail_data,
                technical_id=technical_id,
                meta={}
            )
        except Exception as e2:
            logger.exception(e2)

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
        technical_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="data_sources",
            entity_version=ENTITY_VERSION,
            entity=job_data
        )
        async with httpx.AsyncClient() as client:
            response = await client.get("https://jsonplaceholder.typicode.com/posts/1")
            response.raise_for_status()
            external_data = response.json()

        # Fire and forget processing task that will update the created entity
        asyncio.create_task(process_entity(technical_id, external_data))

        return jsonify({
            "status": "success",
            "message": "Processing started",
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