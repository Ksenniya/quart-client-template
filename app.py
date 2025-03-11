from common.grpc_client.grpc_client import grpc_stream
import asyncio
import logging
import datetime
from dataclasses import dataclass
from typing import Optional

from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request
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

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task
        logger.info("Successfully initialized cyoda")
    except Exception as e:
        logger.exception("Failed to initialize cyoda")
        raise e

# POST endpoint for data_sources.
# The workflow function process_data_sources is applied asynchronously before the entity is persisted.
@app.route('/data_sources', methods=['POST'])
@validate_request(DataSourceParameters)
async def data_sources(data: DataSourceParameters):
    try:
        requested_at = datetime.datetime.utcnow().isoformat()
        # Prepare the initial minimal state for the entity.
        job_data = {
            "status": "processing",
            "requestedAt": requested_at
        }
        # Create a new entity via entity_service.add_item.
        # The workflow function process_data_sources will be invoked asynchronously before persistence.
        technical_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="data_sources",
            entity_version=ENTITY_VERSION,
            entity=job_data,
            )
        return jsonify({
            "status": "success",
            "message": "Processing initiated",
            "job_id": technical_id
        })
    except Exception as e:
        logger.exception("Error in data_sources endpoint")
        return jsonify({"status": "error", "message": str(e)}), 500

# GET endpoint for retrieving processed results.
@app.route('/results', methods=['GET'])
async def results():
    try:
        # Retrieve all items for the data_sources entity.
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
        logger.exception("Error retrieving results")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)