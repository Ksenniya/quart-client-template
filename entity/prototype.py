```python
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass
import httpx
import asyncio
import logging
from datetime import datetime

app = Quart(__name__)
QuartSchema(app)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Local cache for storing greetings
greetings_cache = {}

@dataclass
class GreetRequest:
    name: str

@app.route('/hello', methods=['GET'])
async def hello():
    return jsonify({"message": "Hello, World!"})

@app.route('/greet', methods=['POST'])
@validate_request(GreetRequest)  # Validation for POST must come last
async def greet(data: GreetRequest):
    name = data.name

    if not name:
        return jsonify({"error": "Name is required."}), 400

    # Process the greeting in a separate task
    requested_at = datetime.now()
    job_id = f"greet-{requested_at.timestamp()}"
    greetings_cache[job_id] = {"status": "processing", "requestedAt": requested_at}

    logger.info(f"Processing greeting for {name}...")

    # Fire and forget the processing task
    await asyncio.create_task(process_greeting(job_id, name))

    return jsonify({"message": f"Hello, {name}!"})

@app.route('/greet_by_query', methods=['GET'])
@validate_querystring(GreetRequest)  # Workaround issue: Validation must come first for GET
async def greet_by_query():
    name = request.args.get('name')  # Standard approach to access parameters for GET requests

    # Process the greeting in a separate task
    requested_at = datetime.now()
    job_id = f"greet-{requested_at.timestamp()}"
    greetings_cache[job_id] = {"status": "processing", "requestedAt": requested_at}

    logger.info(f"Processing greeting for {name}...")

    # Fire and forget the processing task
    await asyncio.create_task(process_greeting(job_id, name))

    return jsonify({"message": f"Hello, {name}!"})

async def process_greeting(job_id, name):
    try:
        # Simulating an external API call (TODO: Replace with real API)
        async with httpx.AsyncClient() as client:
            # TODO: Replace with real API URL
            response = await client.get(f'https://api.example.com/greet?name={name}')
            # Log the response from the external API
            logger.info(f"Received response for {name}: {response.text}")

        # Update local cache status
        greetings_cache[job_id]["status"] = "completed"
        logger.info(f"Greeting processed for {name} successfully.")

    except Exception as e:
        logger.exception(e)
        greetings_cache[job_id]["status"] = "failed"

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```