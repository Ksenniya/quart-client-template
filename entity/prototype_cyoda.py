Below is one refactored version of the prototype where all direct dictionary‐accesses (the builds_cache) have been replaced with calls to the external entity_service. In this example we use the entity_service functions (add_item, get_item, update_item) for creating, retrieving, and updating “build” items. (For brevity we leave statistics “logic” and the TeamCity cancellation calls unchanged.) Note that we add the startup code, import the ENTITY_VERSION constant, and use the cyoda_token and entity_service from the provided modules.

────────────────────────────────────────────────────────────
#!/usr/bin/env python3
import asyncio
import datetime
import uuid
import copy

from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response  # See comment below
import aiohttp

# Import the external entity service and constants.
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

# ----- Startup: initialize Cyoda -----
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

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

# ----- Helper Functions -----

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

# As before, a placeholder for calling the TeamCity API.
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
    Now uses the entity_service update_item call to update the build status.
    TODO: Replace with actual logic.
    """
    await asyncio.sleep(5)  # Simulated delay.
    # Retrieve current build data.
    build_data = await entity_service.get_item(
        token=cyoda_token,
        entity_model="build",
        entity_version=ENTITY_VERSION,
        technical_id=build_id
    )
    if not build_data:
        print(f"Build id {build_id} not found in external service during processing.")
        return

    # Update the build status to finished and add details.
    updated = copy.deepcopy(build_data)
    updated["status"] = "finished"
    updated["details"] = {
        "info": f"{deployment_type} deployment completed successfully"
    }
    await entity_service.update_item(
        token=cyoda_token,
        entity_model="build",
        entity_version=ENTITY_VERSION,
        entity=updated,
        meta={}
    )

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
    # Use the build_id from TeamCity or fallback to a generated uuid.
    teamcity_build_id = tc_response.get("build_id", str(uuid.uuid4()))
    
    # Prepare the build data to persist via the external entity_service.
    build_data = {
        "teamcity_build_id": teamcity_build_id,
        "status": "processing",
        "requestedAt": current_timestamp(),
        "type": "cyoda-env",
        "details": {}
    }
    # Create the build record externally.
    new_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="build",
        entity_version=ENTITY_VERSION,
        entity=build_data
    )

    # Fire and forget background task.
    asyncio.create_task(process_build(new_id, "cyoda-env"))

    return DeployResponse(build_id=new_id, message="Deployment started"), 201

@app.route("/api/v1/deploy/cyoda-env/status", methods=["POST"])
@validate_request(BuildStatusRequest)
@validate_response(BuildStatusResponse, 200)
async def status_cyoda_env(data: BuildStatusRequest):
    if not validate_bearer_token():
        return jsonify({"error": "Unauthorized"}), 401

    build_data = await entity_service.get_item(
        token=cyoda_token,
        entity_model="build",
        entity_version=ENTITY_VERSION,
        technical_id=data.build_id
    )
    if not build_data:
        return jsonify({"error": "Invalid or unknown build_id"}), 400

    return BuildStatusResponse(status=build_data.get("status", "unknown"),
                               details=build_data.get("details", {})), 200

@app.route("/api/v1/deploy/cyoda-env/statistics", methods=["POST"])
@validate_request(BuildStatusRequest)
@validate_response(StatisticsResponse, 200)
async def statistics_cyoda_env(data: BuildStatusRequest):
    if not validate_bearer_token():
        return jsonify({"error": "Unauthorized"}), 401

    build_data = await entity_service.get_item(
        token=cyoda_token,
        entity_model="build",
        entity_version=ENTITY_VERSION,
        technical_id=data.build_id
    )
    if not build_data:
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
    teamcity_build_id = tc_response.get("build_id", str(uuid.uuid4()))
    
    build_data = {
        "teamcity_build_id": teamcity_build_id,
        "status": "processing",
        "requestedAt": current_timestamp(),
        "type": "user-app",
        "details": {}
    }
    new_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="build",
        entity_version=ENTITY_VERSION,
        entity=build_data
    )

    asyncio.create_task(process_build(new_id, "user-app"))

    return DeployResponse(build_id=new_id, message="Deployment started"), 201

@app.route("/api/v1/deploy/user-app/status", methods=["POST"])
@validate_request(BuildStatusRequest)
@validate_response(BuildStatusResponse, 200)
async def status_user_app(data: BuildStatusRequest):
    if not validate_bearer_token():
        return jsonify({"error": "Unauthorized"}), 401

    build_data = await entity_service.get_item(
        token=cyoda_token,
        entity_model="build",
        entity_version=ENTITY_VERSION,
        technical_id=data.build_id
    )
    if not build_data:
        return jsonify({"error": "Invalid or unknown build_id"}), 400

    return BuildStatusResponse(status=build_data.get("status", "unknown"),
                               details=build_data.get("details", {})), 200

@app.route("/api/v1/deploy/user-app/statistics", methods=["POST"])
@validate_request(BuildStatusRequest)
@validate_response(StatisticsResponse, 200)
async def statistics_user_app(data: BuildStatusRequest):
    if not validate_bearer_token():
        return jsonify({"error": "Unauthorized"}), 401

    build_data = await entity_service.get_item(
        token=cyoda_token,
        entity_model="build",
        entity_version=ENTITY_VERSION,
        technical_id=data.build_id
    )
    if not build_data:
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

    build_data = await entity_service.get_item(
        token=cyoda_token,
        entity_model="build",
        entity_version=ENTITY_VERSION,
        technical_id=data.build_id
    )
    if not build_data:
        return jsonify({"error": "Invalid or unknown build_id"}), 400

    cancellation_payload = {
        "comment": "Canceling a queued build",
        "readdIntoQueue": False
    }

    try:
        async with aiohttp.ClientSession() as session:
            cancel_url = f"https://teamcity.cyoda.org/app/rest/builds/id:{data.build_id}"
            async with session.post(cancel_url, json=cancellation_payload) as resp:
                await resp.json()  # Process the response if needed.
    except Exception as e:
        print(f"Error cancelling build: {e}")
        # Fall back silently; in production, you might return an error.

    # Update the build status to 'canceled'
    updated = copy.deepcopy(build_data)
    updated["status"] = "canceled"
    await entity_service.update_item(
        token=cyoda_token,
        entity_model="build",
        entity_version=ENTITY_VERSION,
        entity=updated,
        meta={}
    )

    return CancelResponse(message="Build canceled", build_id=data.build_id), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
────────────────────────────────────────────────────────────

Notes:
1. All calls to the local builds_cache dictionary have been removed. Instead, new build items are added via entity_service.add_item and later retrieved or updated via entity_service.get_item and entity_service.update_item.
2. The returned id from add_item is included in the DeployResponse so that clients can use it to query build status.
3. The process_build function now retrieves the build via the external service before updating its status.
4. Error handling remains minimal (as in the original prototype)—in production you would add more robust error checking and retry logic.

This should satisfy the requirement of using the external entity_service in place of local in‑memory dictionaries while preserving the existing endpoint routes and business logic.