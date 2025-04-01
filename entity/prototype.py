```python
from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import httpx
import asyncio
import logging

# Initialize logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize Quart app
app = Quart(__name__)
QuartSchema(app)

# In-memory cache for entities
entity_job = {}

async def fetch_external_data(param):
    # TODO: Replace with real API URL and logic
    async with httpx.AsyncClient() as client:
        response = await client.get(f'https://api.example.com/data?param={param}')
        response.raise_for_status()  # Raise an error for bad responses
        return response.json()

async def process_entity(job_id, data):
    # Simulate processing
    await asyncio.sleep(2)  # Simulate some processing delay
    logger.info(f'Processing {job_id} completed with data: {data}')

@app.route('/process', methods=['POST'])
async def process():
    data = await request.get_json()
    param = data.get('param')  # Extract parameter from request JSON
    requested_at = data.get('requestedAt')  # Example of additional data

    # Fetch external data
    try:
        external_data = await fetch_external_data(param)
    except Exception as e:
        logger.exception(e)
        return jsonify({'error': 'Failed to fetch external data'}), 500

    # Mock processing job creation
    job_id = len(entity_job) + 1
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}
    
    # Fire and forget the processing task
    await asyncio.create_task(process_entity(job_id, external_data))

    return jsonify({"job_id": job_id, "status": "processing"}), 202

@app.route('/results/<int:job_id>', methods=['GET'])
async def get_results(job_id):
    if job_id not in entity_job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(entity_job[job_id]), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```