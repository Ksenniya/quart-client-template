from common.grpc_client.grpc_client import grpc_stream
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

from common.config.config import ACCESS_TOKEN, ENTITY_VERSION, TEAMCITY_HOST
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

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
    return {"status": 200}


def _get_user_from_token(auth_header: str):
    if not auth_header:
        return None
    parts = auth_header.split(" ")
    if len(parts) != 2:
        return None
    token = parts[1]
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        user_name = decoded.get("sub")
        return user_name
    except Exception as e:
        logger.exception("Failed to decode JWT: %s", e)
        return None


# ---------------------------------------------------------------------
# App Initialization and CORS/Error Handlers
# ---------------------------------------------------------------------
app = Quart(__name__)
QuartSchema(app)


@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))


@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task


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
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if ENABLE_AUTH:
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return jsonify({"error": "Missing Authorization header"}), 401
            user_name = _get_user_from_token(auth_header)
            if not user_name:
                raise UnauthorizedAccessException("Invalid or missing token")
            resp = await send_get_request(user_name, API_URL, "v1")
            if not resp or (resp.get("status") == 401):
                raise UnauthorizedAccessException("Invalid token")
            kwargs["user_name"] = user_name
        return await func(*args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------
# Data Models for Request Validation
# ---------------------------------------------------------------------
@dataclass
class DeployCyodaEnvRequest:
    pass


@dataclass
class DeployUserAppRequest:
    repository_url: str
    is_public: str


@dataclass
class BuildStatusRequest:
    build_id: str  # Updated to job_id


@dataclass
class CancelDeploymentRequest:
    build_id: str  # Updated to job_id
    comment: str
    readIntoQueue: bool


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
    TEAMCITY_BASE_URL = f"{TEAMCITY_HOST}/app/rest"
    url = f"{TEAMCITY_BASE_URL}/buildQueue"
    payload = {
        "buildType": {"id": build_type},
        "properties": {"property": properties},
    }
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.exception("Error triggering TeamCity build: %s", e)
            return {}


async def fetch_teamcity_resource(url: str, error_msg: str) -> Dict[str, Any]:
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


def filter_status_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "state": response_data.get("state"),
        "statistics": response_data.get("statistics"),
        "status": response_data.get("status"),
        "statusText": response_data.get("statusText")
    }


async def verify_user_namespace(job_id: str, user_name: str) -> bool:
    return True


# ---------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------
async def trigger_deployment(pipeline_name: str, properties: list):
    """Trigger a deployment and create a job record."""
    teamcity_response = await trigger_teamcity(pipeline_name, properties)
    if not teamcity_response:
        return None, jsonify({"error": "Failed to trigger deployment"}), 500

    # Normalize the build id
    build_id_raw = str(teamcity_response.get("id") or teamcity_response.get("build_id") or "unknown")
    requested_at = datetime.utcnow().isoformat()
    job_record = {"build_id": build_id_raw, "status": "processing", "requestedAt": requested_at}
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="job",
        entity_version=ENTITY_VERSION,
        entity=job_record,
    )
    return job_id, None, None

async def get_job_by_build_id(build_id: str):
    """Retrieve a job by build/job ID."""
    return await entity_service.get_item(
        token=cyoda_token,
        entity_model="job",
        entity_version=ENTITY_VERSION,
        technical_id=build_id
    )

async def fetch_teamcity_data(url: str, error_message: str, error_return: str):
    """Fetch data from TeamCity and handle errors."""
    response_data = await fetch_teamcity_resource(url, error_message)
    if not response_data:
        return None, jsonify({"error": error_return}), 500
    return response_data, None, None

async def fetch_status(job: dict):
    """Fetch and filter the status from TeamCity."""
    TEAMCITY_BASE_URL = f"{TEAMCITY_HOST}/app/rest"
    url = f"{TEAMCITY_BASE_URL}/buildQueue/id:{job['build_id']}"
    response_data, err_resp, err_code = await fetch_teamcity_data(url, "Error retrieving Cyoda environment status", "Failed to retrieve status")
    if err_resp:
        return None, err_resp, err_code
    return jsonify(filter_status_response(response_data)), None, None

async def fetch_statistics(job: dict):
    """Fetch statistics data from TeamCity."""
    TEAMCITY_BASE_URL = f"{TEAMCITY_HOST}/app/rest"
    url = f"{TEAMCITY_BASE_URL}/builds/id:{job['build_id']}/statistics/"
    response_data, err_resp, err_code = await fetch_teamcity_data(url, "Error retrieving Cyoda environment statistics", "Failed to retrieve statistics")
    if err_resp:
        return None, err_resp, err_code
    return jsonify(response_data), None, None

# ---------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------
@app.route("/deploy/cyoda-env", methods=["POST"])
@validate_request(DeployCyodaEnvRequest)
@auth_required
async def deploy_cyoda_env(data: DeployCyodaEnvRequest, *, user_name: str):
    transformed = transform_user(user_name)
    properties = [
        {"name": "user_defined_keyspace", "value": transformed["keyspace"]},
        {"name": "user_defined_namespace", "value": transformed["namespace"]},
        {"name": "user_env_name", "value": user_name}
    ]
    job_id, err_resp, err_code = await trigger_deployment("KubernetesPipeline_CyodaSaas", properties)
    if err_resp:
        return err_resp, err_code
    return jsonify({"build_id": job_id})

@app.route("/deploy/user_app", methods=["POST"])
@validate_request(DeployUserAppRequest)
@auth_required
async def deploy_user_app(data: DeployUserAppRequest, *, user_name: str):
    transformed = transform_user(user_name)
    properties = [
        {"name": "repository_url", "value": data.repository_url},
        {"name": "user_defined_namespace", "value": transformed["namespace"]},
        {"name": "user_env_name", "value": user_name}
    ]
    job_id, err_resp, err_code = await trigger_deployment("KubernetesPipeline_CyodaSaasUserEnv", properties)
    if err_resp:
        return err_resp, err_code
    return jsonify({"build_id": job_id})

@validate_request(BuildStatusRequest)
@app.route("/deploy/cyoda-env/status", methods=["GET"])
@auth_required
async def get_cyoda_env_status(*, user_name):
    build_id = request.args.get("build_id")
    job = await get_job_by_build_id(build_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    response, err_resp, err_code = await fetch_status(job)
    if err_resp:
        return err_resp, err_code
    return response

@validate_request(BuildStatusRequest)
@app.route("/deploy/user_app/status", methods=["GET"])
@auth_required
async def get_user_app_status(*, user_name):
    build_id = request.args.get("build_id")
    job = await get_job_by_build_id(build_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    response, err_resp, err_code = await fetch_status(job)
    if err_resp:
        return err_resp, err_code
    return response

@validate_request(BuildStatusRequest)
@app.route("/deploy/cyoda-env/statistics", methods=["GET"])
@auth_required
async def get_cyoda_env_statistics(*, user_name):
    build_id = request.args.get("build_id")
    job = await get_job_by_build_id(build_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    response, err_resp, err_code = await fetch_statistics(job)
    if err_resp:
        return err_resp, err_code
    return response

@validate_request(BuildStatusRequest)
@app.route("/deploy/user_app/statistics", methods=["GET"])
@auth_required
async def get_user_app_statistics(*, user_name):
    build_id = request.args.get("build_id")
    job = await get_job_by_build_id(build_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    response, err_resp, err_code = await fetch_statistics(job)
    if err_resp:
        return err_resp, err_code
    return response


@app.route("/deploy/cancel/user_app", methods=["POST"])
@validate_request(CancelDeploymentRequest)
@auth_required
async def cancel_user_app_deployment(data: CancelDeploymentRequest, *, user_name: str):
    job = await entity_service.get_item(
        token=cyoda_token,
        entity_model="job",
        entity_version=ENTITY_VERSION,
        technical_id=data.build_id  # Updated to job_id
    )
    if not job:
        return jsonify({"error": "Job not found"}), 404

    TEAMCITY_BASE_URL = f"{TEAMCITY_HOST}/app/rest"
    url = f"{TEAMCITY_BASE_URL}/builds/id:{job['build_id']}"  # Use build_id from job
    payload = {
        "comment": data.comment,
        "readdIntoQueue": data.readIntoQueue
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