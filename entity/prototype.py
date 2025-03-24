from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring
import httpx
import asyncio
import logging
from datetime import datetime

app = Quart(__name__)
QuartSchema(app)

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# In-memory cache to mock persistence
entity_jobs = {}
results_cache = []

@dataclass
class HelloQuery:
    name: str = None  # Optional name parameter for hello endpoint
    surname: str = None  # Optional surname parameter for hello endpoint

@dataclass
class ProcessData:
    input_data: dict  # Expecting a dictionary for input data

@app.route('/hello', methods=['GET'])
@validate_querystring(HelloQuery)  # Issue workaround: validation first for GET requests
async def hello():
    query = HelloQuery(**request.args)
    name = query.name if query.name else 'World'
    surname = query.surname if query.surname else ''
    if surname:
        return jsonify({"message": f"Hello, {name} {surname}!"})
    return jsonify({"message": f"Hello, {name}!"})

@app.route('/results', methods=['GET'])
async def get_results():
    return jsonify({"results": results_cache})

@app.route('/process', methods=['POST'])
@validate_request(ProcessData)  # Validation last for POST requests
async def process_data(data: ProcessData):
    field1 = data.input_data.get('field1')
    field2 = data.input_data.get('field2')

    # Fire and forget the processing task
    job_id = len(entity_jobs) + 1
    requested_at = datetime.utcnow()
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}

    await asyncio.create_task(process_entity(job_id, field1, field2))

    return jsonify({"status": "success", "result_id": job_id, "message": "Data processed successfully."})

async def process_entity(job_id, field1, field2):
    try:
        # TODO: Implement your logic here. For now, we will use a placeholder.
        async with httpx.AsyncClient() as client:
            # Using a placeholder URL; replace with a real API endpoint if applicable
            response = await client.get('https://api.example.com/data')  # Placeholder API
            external_data = response.json()

        # Perform calculations (placeholder logic)
        result = f"Processed data with {field1} and {field2} using {external_data}"
        
        # Store the result in the cache
        results_cache.append({
            "id": job_id,
            "data": result,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Update job status
        entity_jobs[job_id]["status"] = "completed"
    except Exception as e:
        logger.exception(e)
        entity_jobs[job_id]["status"] = "failed"

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)