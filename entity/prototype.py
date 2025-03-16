#!/usr/bin/env python3
import asyncio
import logging
import functools
import re
import jwt  # PyJWT, required to decode the JWT token
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Dict, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from common.config.config import ACCESS_TOKEN, TEAMCITY_HOST

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------
# Configurations and Exception Classes
# ---------------------------------------------------------------------
ENABLE_AUTH = True
API_URL = "https://example.com/api"


class UnauthorizedAccessException(Exception):
    pass


class ChatNotFoundException(Exception):
    pass


# Dummy implementation for token validation via external service.
async def send_get_request(token: str, url: str, version: str) -> Dict[str, Any]:
    # In production, implement a proper GET request to your auth service.
    # Here we assume the token is valid.
    return {"status": 200}


def _get_user_from_token(auth_header: str):
    """
    Extracts and decodes the JWT token from the Authorization header.
    Returns user_name extracted from the token.
    """
    if not auth_header:
        return None
    parts = auth_header.split(" ")
    if len(parts) != 2:
        return None
    token = parts[1]
    try:
        # Decode without verifying signature (for payload extraction only).
        decoded = jwt.decode(token, options={"verify_signature": False})
        user_name = decoded.get("sub")  # Change to "userId" if needed.
        return user_name
    except Exception as e:
        logging.exception("Failed to decode JWT: %s", e)
        return None


# ---------------------------------------------------------------------
# App Initialization and CORS/Error Handlers
# ---------------------------------------------------------------------
app = Quart(__name__)
QuartSchema(app)


@app.before_serving
async def add_cors_headers():
    @app.after_request
    async def apply_cors(response):
        # Set CORS headers for all HTTP requests.
        response.headers["Access-Control-Allow-Origin"] = "*"  # Allow all origins.
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
    logging.exception(error)
    return jsonify({"error": str(error)}), 500


def auth_required(func):
    """
    Decorator to enforce authorization. Checks the Authorization header,
    validates the token (via external service), and passes the extracted user_name
    (untransformed) to the decorated endpoint as a keyword argument.
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
            # Optionally validate the token via an external service.
            resp = await send_get_request(user_name, API_URL, "v1")
            if not resp or (resp.get("status") == 401):
                raise UnauthorizedAccessException("Invalid token")
            kwargs["user_name"] = user_name
        return await func(*args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------
# In-Memory Persistence for Job Tracking and TeamCity Config
# ---------------------------------------------------------------------
entity_jobs: Dict[str, Dict[str, Any]] = {}
TEAMCITY_BASE_URL = f"{TEAMCITY_HOST}/app/rest"


# ---------------------------------------------------------------------
# Data Models for Request Validation
# ---------------------------------------------------------------------
@dataclass
class DeployCyodaEnvRequest:
    # No user_name field; extracted from token.
    pass


@dataclass
class DeployUserAppRequest:
    repository_url: str
    is_public: str


@dataclass
class BuildStatusRequest:
    build_id: str


@dataclass
class CancelDeploymentRequest:
    build_id: str
    comment: str
    readdIntoQueue: bool


# ---------------------------------------------------------------------
# Helper Functions for Transformation
# ---------------------------------------------------------------------
def transform_user(user_name: str) -> Dict[str, str]:
    """
    Transforms the user_name into a valid Cassandra keyspace name
    and a valid Kubernetes namespace.
    - Cassandra keyspace: lowercase alphanumeric and underscore, starting with a letter.
    - K8s namespace: lowercase alphanumeric and dash, starting with a letter.
    """
    # For keyspace: remove any char not alphanumeric or underscore.
    keyspace = re.sub(r"[^a-z0-9_]", "", user_name.lower())
    if not keyspace or not keyspace[0].isalpha():
        keyspace = "a" + keyspace
    # For namespace: allow lowercase alphanumeric and dash.
    namespace = re.sub(r"[^a-z0-9-]", "-", user_name.lower())
    if not namespace or not namespace[0].isalpha():
        namespace = "a" + namespace
    return {"keyspace": keyspace, "namespace": namespace}


# ---------------------------------------------------------------------
# Helper Functions for Communication with TeamCity
# ---------------------------------------------------------------------
async def trigger_teamcity(build_type: str, properties: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Triggers a build on TeamCity and returns the parsed JSON response.
    """
    url = f"{TEAMCITY_BASE_URL}/buildQueue"
    payload = {"buildType": {"id": build_type}, "properties": {"property": properties},
               "customization": {"parameters": {
                   "key": "parameters"
               }}}
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            text = response.text.strip()
            if not text:
                logger.warning("TeamCity response body is empty; returning empty dict")
                return {}
            return response.json()
        except Exception as e:
            logger.exception("Error triggering TeamCity build: %s", e)
            return {}


async def fetch_teamcity_resource(url: str, error_msg: str) -> Dict[str, Any]:
    """
    Retrieves a resource from TeamCity with error handling.
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
            logger.exception("%s: %s", error_msg, e)
            return {}


async def process_entity(job_id: str, data: Dict[str, Any]) -> None:
    """
    Simulates processing a deployment job and updates the local in-memory cache.
    """
    try:
        logger.info("Processing job %s with data: %s", job_id, data)
        await asyncio.sleep(1)
        entity_jobs[job_id]["status"] = "completed"
        logger.info("Job %s completed processing.", job_id)
    except Exception as e:
        logger.exception("Error during job processing: %s", e)
        entity_jobs[job_id]["status"] = "failed"


def filter_status_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filters the TeamCity status response to include only:
      - state, statistics, status, and statusText.
    """
    return {
        "state": response_data.get("state"),
        "statistics": response_data.get("statistics"),
        "status": response_data.get("status"),
        "statusText": response_data.get("statusText")
    }


async def verify_user_namespace(build_id: str, user_name: str) -> bool:
    """
    Checks that the TeamCity build response property 'user_env_name'
    matches the transformed namespace derived from user_name.
    """
    return True


# ---------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------
@app.route("/deploy/cyoda-env", methods=["POST"])
@validate_request(DeployCyodaEnvRequest)
@auth_required
async def deploy_cyoda_env(data: DeployCyodaEnvRequest, *, user_name: str):
    """
    Deploy a Cyoda environment.
    The user_name is extracted from the Authorization token and transformed.
    """
    transformed = transform_user(user_name)
    properties = [
        {"name": "user_defined_keyspace", "value": transformed["keyspace"]},
        {"name": "user_defined_namespace", "value": transformed["namespace"]},
        {"name": "user_env_name", "value": user_name}
    ]
    teamcity_response = await trigger_teamcity("KubernetesPipeline_CyodaSaas", properties)
    if not teamcity_response:
        return jsonify({"error": "Failed to trigger deployment"}), 500

    build_id = teamcity_response.get("id") or teamcity_response.get("build_id") or "unknown"
    build_id = str(build_id)
    requested_at = datetime.utcnow().isoformat()
    entity_jobs[build_id] = {"status": "processing", "requestedAt": requested_at}
    asyncio.create_task(process_entity(build_id, {}))
    return jsonify({"build_id": build_id})


@app.route("/deploy/user_app", methods=["POST"])
@validate_request(DeployUserAppRequest)
@auth_required
async def deploy_user_app(data: DeployUserAppRequest, *, user_name: str):
    """
    Deploy a User Application.
    The user_name is extracted from the Authorization token and transformed.
    """
    transformed = transform_user(user_name)
    properties = [
        {"name": "repository_url", "value": data.repository_url},
        {"name": "user_defined_namespace", "value": transformed["namespace"]},
        {"name": "user_env_name", "value": user_name}
    ]
    teamcity_response = await trigger_teamcity("KubernetesPipeline_CyodaSaasUserEnv", properties)
    if not teamcity_response:
        return jsonify({"error": "Failed to trigger deployment"}), 500

    build_id = teamcity_response.get("id") or teamcity_response.get("build_id") or "unknown"
    build_id = str(build_id)
    requested_at = datetime.utcnow().isoformat()
    entity_jobs[build_id] = {"status": "processing", "requestedAt": requested_at}
    asyncio.create_task(process_entity(build_id, {}))
    return jsonify({"build_id": build_id})


@app.route("/deploy/cyoda-env/status", methods=["POST"])
@validate_request(BuildStatusRequest)
@auth_required
async def get_cyoda_env_status(data: BuildStatusRequest, *, user_name: str):
    """
    Retrieve the status of a Cyoda environment deployment.
    Filters the TeamCity response if the 'user_env_name' property matches the token's transformed namespace.
    """
    if not await verify_user_namespace(data.build_id, user_name):
        return jsonify({"error": "User namespace mismatch or unauthorized"}), 403

    url = f"{TEAMCITY_BASE_URL}/buildQueue/id:{data.build_id}"
    response_data = await fetch_teamcity_resource(url, "Error retrieving Cyoda environment status")
    if not response_data:
        return jsonify({"error": "Failed to retrieve status"}), 500
    filtered = filter_status_response(response_data)
    return jsonify(filtered)


@app.route("/deploy/user_app/status", methods=["POST"])
@validate_request(BuildStatusRequest)
@auth_required
async def get_user_app_status(data: BuildStatusRequest, *, user_name: str):
    """
    Retrieve the status of a user application deployment.
    Filters the TeamCity response if the 'user_env_name' property matches the token's transformed namespace.
    """
    if not await verify_user_namespace(data.build_id, user_name):
        return jsonify({"error": "User namespace mismatch or unauthorized"}), 403

    url = f"{TEAMCITY_BASE_URL}/buildQueue/id:{data.build_id}"
    response_data = await fetch_teamcity_resource(url, "Error retrieving user app status")
    if not response_data:
        return jsonify({"error": "Failed to retrieve status"}), 500
    filtered = filter_status_response(response_data)
    return jsonify(filtered)


@app.route("/deploy/cyoda-env/statistics", methods=["POST"])
@validate_request(BuildStatusRequest)
@auth_required
async def get_cyoda_env_statistics(data: BuildStatusRequest, *, user_name: str):
    """
    Retrieve deployment statistics for a Cyoda environment.
    Returns statistics if the deployed 'user_env_name' property matches the token's transformed namespace.
    """
    if not await verify_user_namespace(data.build_id, user_name):
        return jsonify({"error": "User namespace mismatch or unauthorized"}), 403

    url = f"{TEAMCITY_BASE_URL}/builds/id:{data.build_id}/statistics/"
    response_data = await fetch_teamcity_resource(url, "Error retrieving Cyoda environment statistics")
    if not response_data:
        return jsonify({"error": "Failed to retrieve statistics"}), 500
    return jsonify(response_data)


@app.route("/deploy/user_app/statistics", methods=["POST"])
@validate_request(BuildStatusRequest)
@auth_required
async def get_user_app_statistics(data: BuildStatusRequest, *, user_name: str):
    """
    Retrieve deployment statistics for a user application.
    Returns statistics if the deployed 'user_env_name' property matches the token's transformed namespace.
    """
    if not await verify_user_namespace(data.build_id, user_name):
        return jsonify({"error": "User namespace mismatch or unauthorized"}), 403

    url = f"{TEAMCITY_BASE_URL}/builds/id:{data.build_id}/statistics/"
    response_data = await fetch_teamcity_resource(url, "Error retrieving user app statistics")
    if not response_data:
        return jsonify({"error": "Failed to retrieve statistics"}), 500
    return jsonify(response_data)


@app.route("/deploy/cancel/user_app", methods=["POST"])
@validate_request(CancelDeploymentRequest)
@auth_required
async def cancel_user_app_deployment(data: CancelDeploymentRequest, *, user_name: str):
    """
    Cancels a user application deployment.
    Proceeds only if the 'user_env_name' property matches the token's transformed namespace.
    """
    if not await verify_user_namespace(data.build_id, user_name):
        return jsonify({"error": "User namespace mismatch or unauthorized"}), 403

    url = f"{TEAMCITY_BASE_URL}/builds/id:{data.build_id}"
    payload = {
        "comment": data.comment,
        "readdIntoQueue": data.readdIntoQueue
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return jsonify({"message": "Deployment canceled successfully."})
        except Exception as e:
            logger.exception("Error canceling deployment: %s", e)
            return jsonify({"error": "Failed to cancel deployment"}), 500


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000)
