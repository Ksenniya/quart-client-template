```python
from dataclasses import dataclass
from quart import Quart, request
from quart_schema import QuartSchema, validate_request, validate_querystring

app = Quart(__name__)
QuartSchema(app)

@dataclass
class HelloRequest:
    name: str  # Primitive type for validation

# Workaround for validation order due to issue in quart-schema library

@app.route("/hello", methods=["GET"])
@validate_querystring(HelloRequest)  # Validation should be first for GET requests
async def get_hello():
    name = request.args.get('name')  # Accessing parameters for GET requests
    return {"message": f"Hello, {name}!"}

@app.route("/hello", methods=["POST"])
@validate_request(HelloRequest)  # Validation should be last for POST requests
async def create_hello(data: HelloRequest):
    return {"message": f"Hello, {data.name}!"}
```