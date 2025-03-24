from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_querystring
from dataclasses import dataclass
import logging

app = Quart(__name__)
QuartSchema(app)

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@dataclass
class HelloRequest:
    name: str
    surname: str  # Added surname parameter

@app.route('/hello', methods=['GET'])
@validate_querystring(HelloRequest)  # Workaround: validation placed first for GET requests
async def hello():
    name = request.args.get('name', 'World')
    surname = request.args.get('surname', '')  # Added surname extraction
    return jsonify(message=f"Hello, {name} {surname}!")

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)