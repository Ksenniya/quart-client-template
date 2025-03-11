#!/usr/bin/env python3
import asyncio
import uuid
import logging
from datetime import datetime
from dataclasses import dataclass, field

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

# Constant for entity version
ENTITY_VERSION = "1.0"

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

# In-memory entity storage service
class EntityService:
    def __init__(self):
        # Store entities keyed by (entity_model, technical_id)
        self.store = {}

    # Add an entity with a workflow function applied before persistence
    async def add_item(self, token, entity_model, entity_version, entity, workflow):
        # Apply workflow function asynchronously to the entity
        processed_entity = await workflow(entity)
        # Generate a unique technical id for the entity
        item_id = str(uuid.uuid4())
        self.store[(entity_model, item_id)] = processed_entity
        logger.info("Entity added: model=%s, id=%s, data=%s", entity_model, item_id, processed_entity)
        return item_id

    # Get an entity by its technical id
    async def get_item(self, token, entity_model, entity_version, technical_id):
        return self.store.get((entity_model, technical_id))

    # Update an existing entity
    async def update_item(self, token, entity_model, entity_version, entity, technical_id, meta):
        key = (entity_model, technical_id)
        if key in self.store:
            self.store[key].update(entity)
            logger.info("Entity updated: model=%s, id=%s, data=%s", entity_model, technical_id, self.store[key])
            return True
        return False

# Global instances for the service and token
entity_service = EntityService()
cyoda_token = "dummy_token"

# Workflow function for 'job' entity processing.
# This function is applied asynchronously to the job entity before persistence.
async def process_job(entity):
    try:
        resource = entity.get("resource")
        options = entity.get("options", {})
        result = None
        if resource == "pet":
            statuses = options.get("status", ["available"])
            # Construct parameters; API expects comma separated statuses if multiple
            params = {"status": ",".join(statuses) if isinstance(statuses, list) else statuses}
            async with httpx.AsyncClient() as client:
                response = await client.get("https://petstore.swagger.io/v2/pet/findByStatus", params=params)
                response.raise_for_status()
                result = response.json()
        elif resource == "store":
            # Placeholder for store resource processing
            result = {"message": "Store resource processing not implemented", "data": None}
        elif resource == "user":
            # Placeholder for user resource processing
            result = {"message": "User resource processing not implemented", "data": None}
        else:
            result = {"error": f"Unsupported resource '{resource}'."}
        # Update the entity state directly
        entity["data"] = result
        entity["status"] = "completed"
    except Exception as e:
        logger.exception("Error processing job entity")
        entity["data"] = {"error": str(e)}
        entity["status"] = "failed"
    return entity

# Request model for fetching data endpoint
@dataclass
class FetchDataRequest:
    resource: str
    options: dict = field(default_factory=dict)

app = Quart(__name__)
QuartSchema(app)

# Startup hook; can be used for initialization tasks
@app.before_serving
async def startup():
    logger.info("Application startup: initialization complete.")

# Endpoint to initiate data retrieval
@app.route('/api/fetch-data', methods=["POST"])
@validate_request(FetchDataRequest)
async def fetch_data(data: FetchDataRequest):
    try:
        resource = data.resource
        options = data.options
        requested_at = datetime.utcnow().isoformat()
        # Embed resource and options into job data so workflow has necessary context
        job_data = {
            "status": "processing",
            "requestedAt": requested_at,
            "data": None,
            "resource": resource,
            "options": options
        }
        # Create a job entity with the process_job workflow function applied before persistence
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            entity=job_data,
            workflow=process_job  # Workflow function processing the job entity asynchronously
        )
        return jsonify({
            "job_id": job_id,
            "message": "Data retrieval initiated. Check results endpoint for status."
        }), 202
    except Exception as e:
        logger.exception("Error in /api/fetch-data endpoint")
        return jsonify({"error": "Internal Server Error"}), 500

# Endpoint to retrieve job results
@app.route('/api/results/<job_id>', methods=["GET"])
async def get_results(job_id: str):
    try:
        job = await entity_service.get_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
        if not job:
            return jsonify({"error": "Job not found"}), 404
        return jsonify({
            "job_id": job_id,
            "status": job.get("status"),
            "data": job.get("data")
        })
    except Exception as e:
        logger.exception("Error in /api/results endpoint")
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)