#!/usr/bin/env python3
import asyncio
import logging
import functools
import re
import jwt  # PyJWT required for decoding JWT tokens
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Dict, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema  # Data validation disabled per instructions

# ---------------------------------------------------------------------
# Configuration & Logging
# ---------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

ENABLE_AUTH = True
API_URL = "https://example.com/api"  # TODO: Replace with real token validation API if available
TEAMCITY_BASE_URL = "https://teamcity.cyoda.org/app/rest"
ACCESS_TOKEN = "your_access_token_here"  # TODO: Replace with a real access token

# ---------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------
class UnauthorizedAccessException(Exception):
    pass

class ChatNotFoundException(Exception):
    pass

# ---------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------
async def send_get_request(token: str, url: str, version: str) -> Dict[str, Any]:
    """
    Dummy implementation for token validation via an external service.
    TODO: Replace with a real implementation when available.
    """
    # Using real API call with httpx if available (here we use a placeholder)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)  # Simplified for the prototype
            # TODO: Check response content and status as needed.
            if response.status_code == 200:
                return {"status": 200}
            else:
                return {"status": response.status_code}
        except Exception as e:
            logger.exception(e)
            return {"status": 500}

def _get_user_from_token(auth_header: str):
    """
    Extract and decode the JWT token from the Authorization header.
    Returns user_name extracted from the token.
    """
    if not auth_header:
        return None
    parts = auth_header.split(" ")
    if len(parts) != 2:
        return None
    token = parts[1]
    try:
        # Decode without verifying signature for payload extraction only.
        decoded = jwt.decode(token, options={"verify_signature": False})
        user_name = decoded.get("sub")
        return user_name
    except Exception as e:
        logger.exception(e)
        return None

def transform_user(user_name: str) -> Dict[str, str]:
    """
    Transforms the user_name into valid identifiers for Cassandra keyspace and Kubernetes namespace.
    """
    # For keyspace: allow only lowercase letter, numbers, underscore; must start with a letter.
    keyspace = re.sub(r"[^a-z0-9_]", "", user_name.lower())
    if not keyspace or not keyspace[0].isalpha():
        keyspace = "a" + keyspace
    # For namespace: allow lowercase alphanumeric and dash; must start with a letter.
    namespace = re.sub(r"[^a-z0-9-]", "-", user_name.lower())
    if not namespace or not namespace[0].isalpha():
        namespace = "a" + namespace
    return {"keyspace": keyspace, "namespace": namespace}

# ---------------------------------------------------------------------
# Persistence (In-Memory Cache)
# ---------------------------------------------------------------------
entity_jobs: Dict[str, Dict[str, Any]] = {}

# ---------------------------------------------------------------------
# HTTP Helpers for TeamCity Integration
# ---------------------------------------------------------------------
async def trigger_teamcity(build_type: str, properties: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Triggers a build on TeamCity and returns the JSON result.
    """
    url = f"{TEAMCITY_BASE_URL}/buildQueue"
    payload = {"buildType": {"id": build_type}, "properties": {"property": properties}}
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            if not response.text.strip():
                logger.warning("TeamCity response body is empty; returning empty dict")
                return {}
            return response.json()
        except Exception as e:
            logger.exception(e)
            return {}

async def fetch_teamcity_resource(url: str, error_msg: str) -> Dict[str, Any]:
    """
    Retrieves a resource from TeamCity and returns the JSON data.
    """
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.exception(f"{error_msg}: {e}")
            return {}

async def process_entity(job_id: str, data: Dict[str, Any]) -> None:
    """
    Simulates processing a deployment job.
    TODO: Replace with real processing logic when available.
    """
    try:
        logger.info(f"Processing job {job_id} with data: {data}")
        await asyncio.sleep(1)
        entity_jobs[job_id]["status"] = "completed"
        logger.info(f"Job {job_id} completed processing.")
    except Exception as e:
        logger.exception(e)
        entity_jobs[job_id]["status"] = "failed"

def filter_status_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filters TeamCity status response to include only relevant fields.
    """
    return {
        "state": response_data.get("state"),
        "statistics": response_data.get("statistics"),
        "status": response_data.get("status"),
        "statusText": response_data.get("statusText")
    }

async def verify_user_namespace(build_id: str, user_name: str) -> bool:
    """
    Verifies that the TeamCity build's user environment matches the transformed namespace.
    """
    url = f"{TEAMCITY_BASE_URL}/buildQueue/id:{build_id}"
    status_data = await fetch_teamcity_resource(url, "Error retrieving status for namespace verification")
    if not status_data:
        return False
    properties_obj = status_data.get("properties", {})
    prop_list = properties_obj.get("property", [])
    transformed = transform_user(user_name)
    expected_namespace = transformed["namespace"]
    for prop in prop_list:
        if prop.get("name") == "user_env_name" and prop.get("value") == expected_namespace:
            return True
    return False

# ---------------------------------------------------------------------
# App Initialization
# ---------------------------------------------------------------------
app = Quart(__name__)
# Use QuartSchema for dynamic data, but no validation decorators per instructions.
QuartSchema(app)

@app.before_serving
async def add_cors_headers():
    @app.after_request
    async def apply_cors(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

@app.errorhandler(UnauthorizedAccessException)
async def handle_unauthorized_exception(error):
    return jsonify({"error": str(error)}), 401

@app.errorhandler(ChatNotFoundException)
async def handle_chat_not_found_exception(error):
    return jsonify({"error": str(error)}), 404

@app.errorhandler(Exception)
async def handle_any_exception(error):
    logger.exception(error)
    return jsonify({"error": str(error)}), 500

def auth_required(func):
    """
    Decorator to enforce authorization.
    Checks the Authorization header and validates the token.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if ENABLE_AUTH:
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return jsonify({"error": "Missing Authorization header"}), 401
            user_name = _get_user_from_token(auth_header)
            if not user_name:
                raise UnauthorizedAccessException("Invalid or missing token")
            # Optionally, validate token via external service.
            resp = await send_get_request(user_name, API_URL, "v1")
            if not resp or resp.get("status") == 401:
                raise UnauthorizedAccessException("Invalid token")
            kwargs["user_name"] = user_name
        return await func(*args, **kwargs)
    return wrapper

# ---------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------
@app.route("/deploy/cyoda-env", methods=["POST"])
@auth_required
async def deploy_cyoda_env(*, user_name: str):
    """
    Deploy a Cyoda environment.
    """
    transformed = transform_user(user_name)
    properties = [
        {"name": "user_defined_keyspace", "value": transformed["keyspace"]},
        {"name": "user_defined_namespace", "value": transformed["namespace"]},
        {"name": "user_env_name", "value": transformed["namespace"]}
    ]
    teamcity_response = await trigger_teamcity("KubernetesPipeline_CyodaSaas", properties)
    if not teamcity_response:
        return jsonify({"error": "Failed to trigger deployment"}), 500

    # Extract build id from TeamCity response.
    build_id = teamcity_response.get("id") or teamcity_response.get("build_id") or "unknown"
    build_id = str(build_id)
    requested_at = datetime.utcnow().isoformat()
    entity_jobs[build_id] = {"status": "processing", "requestedAt": requested_at}
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(build_id, {}))
    return jsonify({"build_id": build_id})

@app.route("/deploy/user_app", methods=["POST"])
@auth_required
async def deploy_user_app(*, user_name: str):
    """
    Deploy a user application.
    Expects a JSON payload with 'repository_url' and 'is_public'.
    """
    data = await request.get_json()
    if not data or "repository_url" not in data or "is_public" not in data:
        return jsonify({"error": "Invalid request payload"}), 400

    transformed = transform_user(user_name)
    properties = [
        {"name": "repository_url", "value": data["repository_url"]},
        {"name": "user_defined_namespace", "value": transformed["namespace"]},
        {"name": "user_env_name", "value": transformed["namespace"]}
    ]
    teamcity_response = await trigger_teamcity("KubernetesPipeline_CyodaSaasUserEnv", properties)
    if not teamcity_response:
        return jsonify({"error": "Failed to trigger deployment"}), 500

    build_id = teamcity_response.get("id") or teamcity_response.get("build_id") or "unknown"
    build_id = str(build_id)
    requested_at = datetime.utcnow().isoformat()
    entity_jobs[build_id] = {"status": "processing", "requestedAt": requested_at}
    asyncio.create_task(process_entity(build_id, data))
    return jsonify({"build_id": build_id})

@app.route("/deploy/cyoda-env/status", methods=["POST"])
@auth_required
async def get_cyoda_env_status(*, user_name: str):
    """
    Get the status of a Cyoda environment deployment.
    Expects a JSON payload with 'build_id'.
    """
    data = await request.get_json()
    if not data or "build_id" not in data:
        return jsonify({"error": "Invalid request payload"}), 400

    build_id = data["build_id"]
    if not await verify_user_namespace(build_id, user_name):
        return jsonify({"error": "User namespace mismatch or unauthorized"}), 403

    url = f"{TEAMCITY_BASE_URL}/buildQueue/id:{build_id}"
    response_data = await fetch_teamcity_resource(url, "Error retrieving Cyoda environment status")
    if not response_data:
        return jsonify({"error": "Failed to retrieve status"}), 500

    filtered = filter_status_response(response_data)
    return jsonify(filtered)

@app.route("/deploy/user_app/status", methods=["POST"])
@auth_required
async def get_user_app_status(*, user_name: str):
    """
    Get the status of a user application deployment.
    Expects a JSON payload with 'build_id'.
    """
    data = await request.get_json()
    if not data or "build_id" not in data:
        return jsonify({"error": "Invalid request payload"}), 400

    build_id = data["build_id"]
    if not await verify_user_namespace(build_id, user_name):
        return jsonify({"error": "User namespace mismatch or unauthorized"}), 403

    url = f"{TEAMCITY_BASE_URL}/buildQueue/id:{build_id}"
    response_data = await fetch_teamcity_resource(url, "Error retrieving user app status")
    if not response_data:
        return jsonify({"error": "Failed to retrieve status"}), 500

    filtered = filter_status_response(response_data)
    return jsonify(filtered)

@app.route("/deploy/cyoda-env/statistics", methods=["POST"])
@auth_required
async def get_cyoda_env_statistics(*, user_name: str):
    """
    Get deployment statistics for a Cyoda environment.
    Expects a JSON payload with 'build_id'.
    """
    data = await request.get_json()
    if not data or "build_id" not in data:
        return jsonify({"error": "Invalid request payload"}), 400

    build_id = data["build_id"]
    if not await verify_user_namespace(build_id, user_name):
        return jsonify({"error": "User namespace mismatch or unauthorized"}), 403

    url = f"{TEAMCITY_BASE_URL}/builds/id:{build_id}/statistics/"
    response_data = await fetch_teamcity_resource(url, "Error retrieving Cyoda environment statistics")
    if not response_data:
        return jsonify({"error": "Failed to retrieve statistics"}), 500

    return jsonify(response_data)

@app.route("/deploy/user_app/statistics", methods=["POST"])
@auth_required
async def get_user_app_statistics(*, user_name: str):
    """
    Get deployment statistics for a user application.
    Expects a JSON payload with 'build_id'.
    """
    data = await request.get_json()
    if not data or "build_id" not in data:
        return jsonify({"error": "Invalid request payload"}), 400

    build_id = data["build_id"]
    if not await verify_user_namespace(build_id, user_name):
        return jsonify({"error": "User namespace mismatch or unauthorized"}), 403

    url = f"{TEAMCITY_BASE_URL}/builds/id:{build_id}/statistics/"
    response_data = await fetch_teamcity_resource(url, "Error retrieving user app statistics")
    if not response_data:
        return jsonify({"error": "Failed to retrieve statistics"}), 500

    return jsonify(response_data)

@app.route("/deploy/cancel/user_app", methods=["POST"])
@auth_required
async def cancel_user_app_deployment(*, user_name: str):
    """
    Cancel a user application deployment.
    Expects a JSON payload with 'build_id', 'comment', and 'readdIntoQueue'.
    """
    data = await request.get_json()
    if not data or "build_id" not in data or "comment" not in data or "readdIntoQueue" not in data:
        return jsonify({"error": "Invalid request payload"}), 400

    build_id = data["build_id"]
    if not await verify_user_namespace(build_id, user_name):
        return jsonify({"error": "User namespace mismatch or unauthorized"}), 403

    url = f"{TEAMCITY_BASE_URL}/builds/id:{build_id}"
    payload = {
        "comment": data["comment"],
        "readdIntoQueue": data["readdIntoQueue"]
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return jsonify({"message": "Deployment canceled successfully."})
        except Exception as e:
            logger.exception(e)
            return jsonify({"error": "Failed to cancel deployment"}), 500

# ---------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)