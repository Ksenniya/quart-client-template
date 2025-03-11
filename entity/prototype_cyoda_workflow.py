#!/usr/bin/env python3
import asyncio
import uuid
import logging
from datetime import datetime

import httpx
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# External API URL
EXTERNAL_API_URL = "https://petstore.swagger.io/v2/swagger.json"

# Startup initialization for external cyoda service
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@dataclass
class FetchDataRequest:
    data_type: str
    filter: dict = None  # Optional filtering parameters

@dataclass
class ResultsQuery:
    data_id: str

async def process_entity(job_id: str, payload: dict):
    """
    Processes the external API request. Retrieves data from the external API,
    performs any business calculations and updates the job status with the result.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Call the external API to retrieve data.
            response = await client.get(EXTERNAL_API_URL)
            response.raise_for_status()
            external_data = response.json()
        logger.info("External API data retrieved successfully for job_id: %s", job_id)

        # TODO: Process the external_data using payload['data_type'] and payload['filter'] as needed.
        data_type = payload.get("data_type")
        processed_data = external_data  # Placeholder for actual processing logic
        if data_type:
            # TODO: Implement data filtering based on data_type and payload['filter'] if provided.
            processed_data = external_data  # Placeholder for filtered/processed data

        # Retrieve the current job state and update with the processing result.
        # If retrieval fails, fallback to a new structure.
        try:
            job = await entity_service.get_item(
                token=cyoda_token,
                entity_model="job",
                entity_version=ENTITY_VERSION,
                technical_id=job_id
            )
            if not job:
                job = {}
        except Exception as e:
            logger.exception(e)
            job = {}

        job["status"] = "completed"
        job["processedAt"] = datetime.utcnow().isoformat()
        job["data"] = processed_data

        await entity_service.update_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            entity=job,
            technical_id=job_id,
            meta={}
        )
        logger.info("Job %s processed successfully", job_id)
    except Exception as e:
        logger.exception(e)
        try:
            job = await entity_service.get_item(
                token=cyoda_token,
                entity_model="job",
                entity_version=ENTITY_VERSION,
                technical_id=job_id
            )
            if not job:
                job = {}
        except Exception as inner_e:
            logger.exception(inner_e)
            job = {}
        job["status"] = "failed"
        job["error"] = str(e)
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            entity=job,
            technical_id=job_id,
            meta={}
        )

async def process_job(entity: dict):
    # Workflow function applied to 'job' entity before persistence.
    # Add a workflow processed timestamp field.
    entity["workflowProcessedAt"] = datetime.utcnow().isoformat()
    return entity

@app.route("/fetch_data", methods=["POST"])
@validate_request(FetchDataRequest)
async def fetch_data(data: FetchDataRequest):
    try:
        payload = data.__dict__
        if not payload or 'data_type' not in payload:
            return jsonify({"status": "error", "message": "Missing 'data_type' in request"}), 400

        # Create a unique job id and record initial job data.
        job_id = str(uuid.uuid4())
        requested_at = datetime.utcnow().isoformat()
        initial_job_data = {
            "status": "processing",
            "requestedAt": requested_at,
            "data": None
        }
        # Save the job using the external service with workflow processing.
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            entity=initial_job_data,
            workflow=process_job
        )
        logger.info("Started processing job %s at %s", job_id, requested_at)

        # Fire and forget the processing task.
        asyncio.create_task(process_entity(job_id, payload))
        
        return jsonify({
            "status": "success",
            "message": "Data has been fetched and processing has started.",
            "data_id": job_id
        }), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

@validate_querystring(ResultsQuery)
@app.route("/results", methods=["GET"])
async def results():
    try:
        job_id = request.args.get("data_id")
        if not job_id:
            return jsonify({"status": "error", "message": "Missing 'data_id' parameter"}), 400

        job = await entity_service.get_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
        if not job:
            return jsonify({"status": "error", "message": "Data not found"}), 404

        return jsonify({
            "status": "success",
            "data": job
        }), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)