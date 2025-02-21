Below is an updated prototype.py that adds validation to each endpoint. Note that for POST endpoints the decorators are applied in this order:

 – First: the route declaration  
 – Second: @validate_request  
 – Third: @validate_response  

This ordering is a workaround for an existing issue with quart‑schema (see comment below). All request bodies are now validated against simple dataclasses that use only primitives.

-------------------------------------------------------
#!/usr/bin/env python3
import asyncio
import datetime
import uuid

from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response  # See comment below
import aiohttp

app = Quart(__name__)
QuartSchema(app)

# NOTE: For POST endpoints, the decorator order is:
#   @app.route(...)       [first]
#   @validate_request(...) [second]
#   @validate_response(...)[third]
# This is a workaround for a known issue with quart-schema.

# ----- Data Models for Validation -----

@dataclass
class CyodaEnvRequest:
    user_name: str

@dataclass
class DeployResponse:
    build_id: str
    message: str

@dataclass
class BuildStatusRequest:
    build_id: str

@dataclass
class BuildStatusResponse:
    status: str
    details: dict  # Using a dict; TODO: refine type when requirements are clearer.

@dataclass
class StatisticsResponse:
    duration: str
    resources: str

@dataclass
class UserAppRequest:
    repository_url: str
    is_public: bool
    user_name: str

@dataclass
class CancelResponse:
    message: str
    build_id: str

# ----- In-Memory Persistence (Mock) -----
builds_cache = {}

def current_timestamp():
    """Returns current UTC time in ISO format."""
    return datetime.datetime.utcnow().isoformat() + "Z"

def validate_bearer_token():
    """Dummy token validator. TODO: implement real token validation."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    token = auth.split(" ", 1)[1]
    # TODO: Validate token properly.
    return True

# ----- External Call to TeamCity (Mock/Placeholder) -----
async def call_teamcity(endpoint: str, payload: dict) -> dict:
    """
    Calls the external TeamCity API. Returns the JSON response.
    TODO: Enhance error handling and adjust for real API response details.
    """
    url = f"https://teamcity.cyoda.org{endpoint}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                response_data = await resp.json()
                return response_data
    except Exception as e:
        print(f"Error calling TeamCity: {e}")
        # Fallback mock response.
        return {"build_id": str(uuid.uuid4())}

async def process_build(build_id: str, deployment_type: str):
    """
    Simulates asynchronous processing of a build.
    TODO: Replace with actual logic.
    """
    await asyncio.sleep(5)  # Simulated delay.
    builds_cache[build_id]["status"] = "finished"
    builds_cache[build_id]["details"] = {
        "info": f"{deployment_type} deployment completed successfully"
    }

# ----- Endpoints ----- 

@app.route("/api/v1/deploy/cyoda-env", methods=["POST"])
@validate_request(CyodaEnvRequest)
@validate_response(DeployResponse, 201)
async def deploy_cyoda_env(data: CyodaEnvRequest):
    if not validate_bearer_token():
        return jsonify({"error": "Unauthorized"}), 401

    payload = {
        "buildType": {"id": "KubernetesPipeline_CyodaSaas"},
        "properties": {
            "property": [
                {"name": "user_defined_keyspace", "value": data.user_name},
                {"name": "user_defined_namespace", "value": data.user_name}
            ]
        }
    }

    tc_response = await call_teamcity("/app/rest/buildQueue", payload)
    build_id = tc_response.get("build_id", str(uuid.uuid4()))  # Fallback to mock ID

    builds_cache[build_id] = {
        "status": "processing",
        "requestedAt": current_timestamp(),
        "type": "cyoda-env",
        "details": {}
    }

    # Fire and forget task.
    asyncio.create_task(process_build(build_id, "cyoda-env"))

    return DeployResponse(build_id=build_id, message="Deployment started"), 201

@app.route("/api/v1/deploy/cyoda-env/status", methods=["POST"])
@validate_request(BuildStatusRequest)
@validate_response(BuildStatusResponse, 200)
async def status_cyoda_env(data: BuildStatusRequest):
    if not validate_bearer_token():
        return jsonify({"error": "Unauthorized"}), 401

    if data.build_id not in builds_cache:
        return jsonify({"error": "Invalid or unknown build_id"}), 400

    build_info = builds_cache[data.build_id]
    return BuildStatusResponse(status=build_info["status"], details=build_info["details"]), 200

@app.route("/api/v1/deploy/cyoda-env/statistics", methods=["POST"])
@validate_request(BuildStatusRequest)
@validate_response(StatisticsResponse, 200)
async def statistics_cyoda_env(data: BuildStatusRequest):
    if not validate_bearer_token():
        return jsonify({"error": "Unauthorized"}), 401
    if data.build_id not in builds_cache:
        return jsonify({"error": "Invalid or unknown build_id"}), 400

    # TODO: Replace with real statistics computation.
    stats = StatisticsResponse(duration="5 minutes", resources="N/A")
    return stats, 200

@app.route("/api/v1/deploy/user-app", methods=["POST"])
@validate_request(UserAppRequest)
@validate_response(DeployResponse, 201)
async def deploy_user_app(data: UserAppRequest):
    if not validate_bearer_token():
        return jsonify({"error": "Unauthorized"}), 401

    payload = {
        "buildType": {"id": "KubernetesPipeline_CyodaSaasUserEnv"},
        "properties": {
            "property": [
                {"name": "user_defined_keyspace", "value": data.user_name},
                {"name": "user_defined_namespace", "value": data.user_name}
            ]
        }
    }

    tc_response = await call_teamcity("/app/rest/buildQueue", payload)
    build_id = tc_response.get("build_id", str(uuid.uuid4()))

    builds_cache[build_id] = {
        "status": "processing",
        "requestedAt": current_timestamp(),
        "type": "user-app",
        "details": {}
    }

    asyncio.create_task(process_build(build_id, "user-app"))

    return DeployResponse(build_id=build_id, message="Deployment started"), 201

@app.route("/api/v1/deploy/user-app/status", methods=["POST"])
@validate_request(BuildStatusRequest)
@validate_response(BuildStatusResponse, 200)
async def status_user_app(data: BuildStatusRequest):
    if not validate_bearer_token():
        return jsonify({"error": "Unauthorized"}), 401

    if data.build_id not in builds_cache:
        return jsonify({"error": "Invalid or unknown build_id"}), 400

    build_info = builds_cache[data.build_id]
    return BuildStatusResponse(status=build_info["status"], details=build_info["details"]), 200

@app.route("/api/v1/deploy/user-app/statistics", methods=["POST"])
@validate_request(BuildStatusRequest)
@validate_response(StatisticsResponse, 200)
async def statistics_user_app(data: BuildStatusRequest):
    if not validate_bearer_token():
        return jsonify({"error": "Unauthorized"}), 401
    if data.build_id not in builds_cache:
        return jsonify({"error": "Invalid or unknown build_id"}), 400

    # TODO: Replace with real statistics retrieval logic.
    stats = StatisticsResponse(duration="5 minutes", resources="N/A")
    return stats, 200

@app.route("/api/v1/deploy/user-app/cancel", methods=["POST"])
@validate_request(BuildStatusRequest)
@validate_response(CancelResponse, 200)
async def cancel_user_app(data: BuildStatusRequest):
    if not validate_bearer_token():
        return jsonify({"error": "Unauthorized"}), 401
    if data.build_id not in builds_cache:
        return jsonify({"error": "Invalid or unknown build_id"}), 400

    cancellation_payload = {
        "comment": "Canceling a queued build",
        "readdIntoQueue": False
    }

    try:
        async with aiohttp.ClientSession() as session:
            cancel_url = f"https://teamcity.cyoda.org/app/rest/builds/id:{data.build_id}"
            async with session.post(cancel_url, json=cancellation_payload) as resp:
                # TODO: Check response status and adjust error handling.
                await resp.json()  # Using the response; not doing anything in this example.
    except Exception as e:
        print(f"Error cancelling build: {e}")
        # Fall back silently; in production, you might return an error.

    builds_cache[data.build_id]["status"] = "canceled"
    return CancelResponse(message="Build canceled", build_id=data.build_id), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
-------------------------------------------------------

This prototype now applies schema validation (using quart‑schema) to each POST endpoint. Mocks/placeholders (with TODO comments) remain for token validation, external TeamCity API integration, and persistence logic.