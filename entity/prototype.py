import asyncio
import uuid
import datetime
import logging

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

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

@app.route('/fetch-data', methods=['POST'])
async def fetch_data():
    """
    POST /fetch-data:
    Initiates the process to fetch external data and perform business logic.
    """
    try:
        request_data = await request.get_json()
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Invalid JSON payload"}), 400

    # Generate a unique job id and record the request
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()
    job_store[job_id] = {"status": "processing", "requestedAt": requested_at}
    
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, request_data))
    
    return jsonify({
        "fetch_id": job_id,
        "status": "success",
        "message": "Data fetching initiated successfully."
    })

@app.route('/results', methods=['GET'])
async def get_results():
    """
    GET /results:
    Retrieves the processed data for a previously initiated job.
    """
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