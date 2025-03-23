from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_querystring
from dataclasses import dataclass
import logging

app = Quart(__name__)
QuartSchema(app)

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Dataclass for validation
dataclass
class Greeting:
    name: str
    surname: str

@app.route('/hello', methods=['GET'])
@validate_querystring(Greeting)  # Workaround: validation first for GET requests
async def hello():
    name = request.args.get('name', 'World')
    surname = request.args.get('surname', '')
    full_greeting = f"Hello, {name} {surname}!".strip()
    return jsonify({"message": full_greeting})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)