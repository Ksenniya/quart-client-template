import asyncio
import uuid
import logging
from datetime import datetime
import httpx

from quart import Quart, request, jsonify
from quart_schema import QuartSchema

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

app = Quart(__name__)
QuartSchema(app)  # Initialize Quart Schema

# In-memory persistence (cache)
# Key: result_id, Value: job details dict
results_cache = {}

# Constants
EXTERNAL_API_URL = "https://petstore.swagger.io/v2/swagger.json"

async def process_entity(result_id: str, chat_id: str, additional_params: dict):
    """
    Process the entity by fetching external data, performing calculations,
    and storing the processed data in the results_cache.
    """
    try:
        logger.info("Process job started for result_id: %s", result_id)
        async with httpx.AsyncClient() as client:
            response = await client.get(EXTERNAL_API_URL)
            response.raise_for_status()
            external_data = response.json()

        # TODO: Perform any additional data processing, filtering or calculations using additional_params.
        # This is a placeholder processing. Modify as necessary.
        processed_data = {
            "chat_id": chat_id,
            "fetched_at": datetime.utcnow().isoformat(),
            "external_data_summary": f"Fetched {len(external_data)} keys" if isinstance(external_data, dict) else "Data fetched",
            "raw_data": external_data  # In a real scenario, consider not returning the raw data directly.
        }

        # Update the job status and store results in cache
        results_cache[result_id] = {
            "status": "completed",
            "requestedAt": results_cache[result_id]["requestedAt"],
            "data": processed_data
        }
        logger.info("Process job completed for result_id: %s", result_id)
    except Exception as e:
        logger.exception(e)
        # Mark as error in cache
        results_cache[result_id] = {
            "status": "error",
            "requestedAt": results_cache[result_id]["requestedAt"],
            "message": str(e)
        }

@app.route('/fetch-data', methods=['POST'])
async def fetch_data():
    try:
        req_data = await request.get_json()
        chat_id = req_data.get("chat_id")
        additional_params = req_data.get("additional_params", {})

        if not chat_id:
            return jsonify({"status": "error", "message": "chat_id is required"}), 400

        # Generate a unique result/job ID
        result_id = str(uuid.uuid4())
        requested_at = datetime.utcnow().isoformat()

        # Store initial job status in cache
        results_cache[result_id] = {"status": "processing", "requestedAt": requested_at}
        logger.info("Job initiated for result_id: %s at %s", result_id, requested_at)

        # Fire and forget the processing task.
        asyncio.create_task(process_entity(result_id, chat_id, additional_params))

        return jsonify({
            "status": "success",
            "result_id": result_id,
            "details": {"requestedAt": requested_at, "message": "Processing started"}
        }), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/results', methods=['GET'])
async def get_results():
    try:
        result_id = request.args.get("result_id")
        if not result_id:
            return jsonify({"status": "error", "message": "result_id query parameter is required"}), 400

        job_result = results_cache.get(result_id)
        if not job_result:
            return jsonify({"status": "error", "message": "Result not found"}), 404

        return jsonify({
            "status": "success",
            "result": job_result
        }), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)