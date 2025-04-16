from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass
import logging
import asyncio
from datetime import datetime

app = Quart(__name__)
QuartSchema(app)

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Local cache to simulate persistence
entity_job = {}

@dataclass
class GreetRequest:
    name: str

@app.route('/hello', methods=['GET'])
async def hello():
    return jsonify({"message": "Hello World"}), 200

@app.route('/greet', methods=['POST'])
@validate_request(GreetRequest)
async def greet(data: GreetRequest):
    name = data.name.strip()

    if not name:
        return jsonify({"error": "Name is required."}), 400

    requested_at = datetime.now()
    job_id = len(entity_job) + 1
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at, "name": name}

    await process_greet_entity(entity_job[job_id])

    return jsonify({"message": f"Hello, {name}!"}), 200

@app.route('/greet/query', methods=['GET'])
@validate_querystring(GreetRequest)
async def greet_query():
    name = request.args.get('name', '').strip()

    if not name:
        return jsonify({"error": "Name is required."}), 400

    return jsonify({"message": f"Hello, {name}!"}), 200

async def process_supplementary_entity(entity):
    # Placeholder for logic to handle supplementary entity
    # TODO: Implement actual processing logic here
    pass 

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)