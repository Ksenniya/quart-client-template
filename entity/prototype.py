```python
from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import httpx
import asyncio
import logging

app = Quart(__name__)
QuartSchema(app)

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# In-memory cache for jobs
entity_job = {}

async def process_entity(job_id, data):
    # TODO: Add real processing logic here
    # Simulate processing time
    await asyncio.sleep(2)
    logger.info(f"Processed job {job_id} with data: {data}")

@app.route('/submit', methods=['POST'])
async def submit_job():
    data = await request.get_json()
    job_id = len(entity_job) + 1  # Simple job ID generation
    requested_at = asyncio.get_event_loop().time()

    # Store the job in the cache
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}
    
    # Fire and forget the processing task
    await asyncio.create_task(process_entity(job_id, data))

    return jsonify({"job_id": job_id, "status": "processing"}), 202

@app.route('/result/<int:job_id>', methods=['GET'])
async def get_result(job_id):
    job = entity_job.get(job_id)
    if job:
        return jsonify(job), 200
    else:
        return jsonify({"error": "Job not found"}), 404

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```

This prototype provides a basic structure for your Quart application with endpoints for submitting jobs and retrieving results. It includes basic logging and uses an in-memory dictionary as a temporary cache for job status. Adjust the processing logic as needed based on future requirements.