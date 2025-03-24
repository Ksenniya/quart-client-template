from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_querystring
import logging

app = Quart(__name__)
QuartSchema(app)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dataclass
class HelloResponse:
    status: str
    data: dict

@dataclass
class HelloRequest:
    name: str  # Added name parameter

@app.route('/hello', methods=['GET'])
@validate_querystring(HelloRequest)  # Workaround for validation logic
async def hello():
    name = request.args.get('name')  # Retrieve name from query parameters
    response = HelloResponse(status="success", data={"message": f"Hello, {name}!"})
    return jsonify(response.__dict__)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)