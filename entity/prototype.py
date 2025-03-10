import asyncio
import uuid
import datetime
import logging

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data models for request validation

@dataclass
class FetchDataRequest:
    external_api: str  # Expected to be "petstore"
    # TODO: Add more primitive fields as needed for parameters.

@dataclass
class ResultsQuery:
    fetch_id: str

# Local in-memory cache for job persistence
job_store = {}

async def process_entity(job_id: str, request_data: dict):
    """
    Process the entity: fetch data from external API and update the job store.
    TODO: Add any necessary processing or calculations on the fetched data.
    """
    external_api_url = "https://petstore.swagger.io/v2/swagger.json"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(external_api_url)
            response.raise_for_status()
            data = response.json()
            # TODO: Perform any business-specific calculations or transformations on 'data' as needed.
            job_store[job_id]["data"] = data
            job_store[job_id]["status"] = "completed"
            logger.info(f"Job {job_id} completed successfully.")
        except Exception as e:
            logger.exception(e)
            job_store[job_id]["status"] = "failed"
            job_store[job_id]["error"] = str(e)

# For POST requests: route decorator comes first, then validate_request (workaround for quart-schema issue)
@app.route('/fetch-data', methods=['POST'])
@validate_request(FetchDataRequest)
async def fetch_data(data: FetchDataRequest):
    """
    POST /fetch-data:
    Initiates the process to fetch external data and perform business logic.
    """
    # Use validated request data (data.external_api)
    if data.external_api.lower() != "petstore":
        return jsonify({"error": "Unsupported external_api value. Expected 'petstore'."}), 400

    # Generate a unique job id and record the request
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()
    job_store[job_id] = {"status": "processing", "requestedAt": requested_at}
    
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, data.__dict__))
    
    return jsonify({
        "fetch_id": job_id,
        "status": "success",
        "message": "Data fetching initiated successfully."
    })

# For GET requests: validate_querystring decorator should be first due to known issue/workaround.
@validate_querystring(ResultsQuery)
@app.route('/results', methods=['GET'])
async def get_results():
    """
    GET /results:
    Retrieves the processed data for a previously initiated job.
    """
    # Access fetch_id using standard approach for GET query parameters.
    fetch_id = request.args.get('fetch_id')
    if not fetch_id or fetch_id not in job_store:
        return jsonify({"error": "Invalid or missing fetch_id"}), 400
    
    result = job_store[fetch_id]
    return jsonify({
        "fetch_id": fetch_id,
        "status": result["status"],
        "data": result.get("data", {})
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)