Below is an example implementation that follows the instructions. In this snippet, POST/PUT requests use @validate_request (and @validate_response when needed), GET requests with query parameters use @validate_querystring (placed before @app.route), and GET requests with only path parameters use no validation.

------------------------------------------------
#!/usr/bin/env python3
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# A simple dataclass representing a Todo item.
# (Note: Only primitive types are used for the fields.)
@dataclass
class Todo:
    task: str

# POST (or PUT) endpoint:
# The decorators validate that the request JSON body matches the Todo schema.
# Additionally, the response will be validated against the Todo schema with HTTP 201.
@app.route("/test", methods=["POST"])
@validate_request(Todo)
@validate_response(Todo, 201)
async def create_todo(data: Todo):
    # Here you would normally persist the Todo.
    # For demo purposes, we simply return the data back.
    return jsonify(data), 201

# GET endpoint with query parameters:
# Use @validate_querystring first so that the incoming query string is validated against Todo.
# Although the query string is validated, you must access these values using the standard request.args approach.
@validate_querystring(Todo)  # This decorator must be placed before @app.route.
@app.route("/test", methods=["GET"])
async def get_todo():
    # Retrieve query parameters using request.args.
    # Even though the query string is validated, do not declare a parameter with type Todo.
    task_param = request.args.get("task")
    return jsonify({"task": task_param})  # Return the value of the 'task' parameter.

# GET endpoint without request body or query parameters validation:
# Only path parameters are used in this route. No validation is needed.
@app.route("/companies/<string:id>/lei", methods=["GET"])
async def get_company_lei(id: str):
    # For demonstration, assume the LEI is fetched or computed somehow.
    lei = "dummy-lei-for-" + id
    return jsonify({"id": id, "lei": lei})

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8000)
------------------------------------------------

Key points in this implementation:
1. POST/PUT endpoints use @validate_request (and optionally @validate_response) to enforce that the request body (and response) conform to the Todo schema.
2. GET endpoints with query parameters are decorated with @validate_querystring (placed before @app.route) and then access parameters with request.args.
3. GET endpoints that use only URL (path) parameters do not require any request validation.

This follows the examples provided by the quart-schema library.