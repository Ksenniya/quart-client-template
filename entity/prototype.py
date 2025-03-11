import asyncio
import logging
import datetime

from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import httpx

app = Quart(__name__)
QuartSchema(app)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Local in-memory caches for processed results and job tracking
results_cache = {}
entity_jobs = {}

async def process_entity(job, external_data):
    try:
        # TODO: Replace this with actual business logic calculations if needed.
        # For the prototype, we'll simply combine the title and body as a processed result.
        processed_result = f"Processed: {external_data.get('title', '')} & {external_data.get('body', '')}"
        job_id = job["job_id"]
        results_cache[job_id] = {
            "id": external_data.get("id"),
            "data": {
                "title": external_data.get("title"),
                "body": external_data.get("body"),
                "processedResult": processed_result
            }
        }
        job["status"] = "done"
        logger.info(f"Processed entity job {job_id}")
    except Exception as e:
        logger.exception(e)
        job["status"] = "failed"

@app.route('/data_sources', methods=['POST'])
async def data_sources():
    try:
        requested_at = datetime.datetime.utcnow().isoformat()
        # Using a simple incremental id as job id for the prototype.
        job_id = str(len(entity_jobs) + 1)
        entity_jobs[job_id] = {"job_id": job_id, "status": "processing", "requestedAt": requested_at}

        async with httpx.AsyncClient() as client:
            response = await client.get("https://jsonplaceholder.typicode.com/posts/1")
            response.raise_for_status()
            external_data = response.json()

        # Fire and forget the processing task.
        asyncio.create_task(process_entity(entity_jobs[job_id], external_data))

        return jsonify({
            "status": "success",
            "message": "Processing started",
            "job_id": job_id
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/results', methods=['GET'])
async def results():
    try:
        # Return the stored results from our in-memory cache.
        return jsonify({
            "status": "success",
            "results": list(results_cache.values())
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)