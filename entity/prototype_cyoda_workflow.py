Below is a complete, refactored version of the application. In this version all logic related to entity processing is moved into dedicated workflow functions that are invoked just before persisting an entity. In particular, rather than “fire‐and‐forget” scheduling being done in the controller (endpoints), the build workflow (process_build_workflow) both performs data modifications and schedules asynchronous processing. We also add error handling (with try/except) around scheduling to prevent issues that might otherwise lead to an inconsistent state. Note that both endpoints and workflow functions no longer duplicate logic, keeping the controllers lean and the business logic centralized.

──────────────────────────────────────────────────────────────
#!/usr/bin/env python3
import asyncio
import datetime
import uuid
import copy
import logging

from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response
import aiohttp

# Import the external entity service and constants.
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

# Configure logging for the module.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    details: dict   # A dictionary to hold any details.

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
    """Dummy token validator. In production, implement real token checks."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    # Optionally, perform additional checks on the token here.
    return True

async def call_teamcity(endpoint: str, payload: dict) -> dict:
    """
    Calls the external TeamCity API. Returns the JSON response.
    If any error occurs, logs the error and returns a fallback build_id.
    """
    url = f"https://teamcity.cyoda.org{endpoint}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                response_data = await resp.json()
                return response_data
    except Exception as e:
        logger.error(f"Error calling TeamCity: {e}")
        # Fallback in case of errors.
        return {"build_id": str(uuid.uuid4())}

# ----- Workflow Functions -----
#
# This workflow function is designed to be passed into the entity_service.add_item call.
# It applies business logic and schedules further processing (if applicable) before persistence.
#
async def process_build_workflow(entity):
    """
    Process the build entity before it is persisted to the external service.
    
    1. Ensures required fields (such as timestamp and workflow flag) are set.
    2. Schedules asynchronous background processing (if teamcity_build_id is available and valid)
       using asyncio.create_task. We wrap scheduling in try/except to log any issues.
    3. Returns the modified entity.
    
    IMPORTANT: This workflow function must not trigger any persistence on new entities of the same
    model to avoid recursion.
    """
    # Ensure that the timestamp is set if missing.
    if "requestedAt" not in entity:
        entity["requestedAt"] = current_timestamp()
    
    # Indicate that the workflow was applied.
    entity["workflowApplied"] = True

    # Schedule further asynchronous processing in background.
    # We check for both teamcity_build_id and type to schedule processing.
    teamcity_build_id = entity.get("teamcity_build_id")
    build_type = entity.get("type")
    if teamcity_build_id and build_type:
        try:
            # Schedule processing without awaiting.
            asyncio.create_task(process_build(teamcity_build_id, build_type))
            logger.info(f"Scheduled asynchronous processing for build {teamcity_build_id} of type {build_type}.")
        except Exception as e:
            # Log error but do not prevent persistence.
            logger.error(f"Error scheduling asynchronous processing for build {teamcity_build_id}: {e}")
    else:
        logger.warning("Entity missing teamcity_build_id or type; skipping scheduling of async processing.")
    
    return entity

async def process_build(teamcity_build_id: str, deployment_type: str):
    """
    Simulates asynchronous processing of a build.
    
    This function:
      • Waits for a simulated delay.
      • Retrieves the current build data from the external service.
      • Updates its status as 'finished' along with deployment details.
    
    Potential issues handled:
      - If the build cannot be retrieved (e.g. wrong id), log the error.
      - Use deepcopy to avoid mutating the retrieved object.
    """
    logger.info(f"Starting background processing for build {teamcity_build_id}.")
    try:
        # Simulated delay (e.g., waiting for an external process).
        await asyncio.sleep(5)
    except Exception as e:
        logger.error(f"Error during simulated delay for build {teamcity_build_id}: {e}")
    
    # Retrieve the current build data.
    build_data = await entity_service.get_item(
        token=cyoda_token,
        entity_model="build",
        entity_version=ENTITY_VERSION,
        technical_id=teamcity_build_id
    )
    if not build_data:
        logger.error(f"Build id {teamcity_build_id} not found in external service during processing.")
        return

    # Create a copy of the build data and update its status and details.
    updated = copy.deepcopy(build_data)
    updated["status"] = "finished"
    updated["details"] = {
        "info": f"{deployment_type} deployment completed successfully"
    }
    try:
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="build",
            entity_version=ENTITY_VERSION,
            entity=updated,
            meta={}
        )
        logger.info(f"Build {teamcity_build_id} marked as finished.")
    except Exception as e:
        logger.error(f"Error updating build {teamcity_build_id}: {e}")

# ----- Endpoints -----
#
# In these endpoints the only responsibilities are to:
#   1. Validate the incoming request.
#   2. Prepare the entity data.
#   3. Call the entity_service.add_item (or get/update_item) with the proper workflow.
#   4. Return a lightweight response.
#

@app.route("/api/v1/deploy/cyoda-env", methods=["POST"])
@validate_request(CyodaEnvRequest)
@validate_response(DeployResponse, 201)
async def deploy_cyoda_env(data: CyodaEnvRequest):
    if not validate_bearer_token():
        return jsonify({"error": "Unauthorized"}), 401

    # Prepare payload for TeamCity.
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
    # Either take the provided build_id or generate a new one.
    teamcity_build_id = tc_response.get("build_id", str(uuid.uuid4()))
    
    # Prepare the build data to be persisted.
    build_data = {
        "teamcity_build_id": teamcity_build_id,
        "status": "processing",
        # Although process_build_workflow will add timestamp if missing,
        # you may still include it here if desired.
        "requestedAt": current_timestamp(),
        "type": "cyoda-env",
        "details": {}
    }
    # Persist the build record with workflow processing.
    new_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="build",
        entity_version=ENTITY_VERSION,
        entity=build_data,
        workflow=process_build_workflow
    )

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

    return BuildStatusResponse(
        status=build_data.get("status", "unknown"),
        details=build_data.get("details", {})
    ), 200

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

    # For demonstration, we return mock statistics.
    stats = StatisticsResponse(duration="5 minutes", resources="N/A")
    return stats, 200

@app.route("/api/v1/deploy/user-app", methods=["POST"])
@validate_request(UserAppRequest)
@validate_response(DeployResponse, 201)
async def deploy_user_app(data: UserAppRequest):
    if not validate_bearer_token():
        return jsonify({"error": "Unauthorized"}), 401

    # Prepare payload for TeamCity (User App pipeline).
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
        entity=build_data,
        workflow=process_build_workflow
    )

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

    return BuildStatusResponse(
        status=build_data.get("status", "unknown"),
        details=build_data.get("details", {})
    ), 200

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
                await resp.json()  # Optionally process TeamCity response.
    except Exception as e:
        logger.error(f"Error cancelling build: {e}")
        # In production, you might wish to alert or otherwise handle the error.

    # Update the build status in the external service.
    updated = copy.deepcopy(build_data)
    updated["status"] = "canceled"
    try:
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="build",
            entity_version=ENTITY_VERSION,
            entity=updated,
            meta={}
        )
        logger.info(f"Build {data.build_id} successfully canceled.")
    except Exception as e:
        logger.error(f"Error updating canceled build {data.build_id}: {e}")

    return CancelResponse(message="Build canceled", build_id=data.build_id), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
──────────────────────────────────────────────────────────────

Explanation and Potential Issues Prevented:
1. Business Logic Isolation – All data modifications and asynchronous task scheduling are handled in process_build_workflow. Endpoints simply prepare and pass in the entity.
2. Asynchronous Scheduling – The workflow function safely wraps asyncio.create_task in try/except so that failures in scheduling do not block persistence.
3. Recursion Prevention – The workflow function performs no calls that would lead to adding an entity of the same model (which would cause infinite recursion).
4. Error Logging – Errors during TeamCity calls, scheduling, or updating are logged. This improves visibility and robustness.
5. Minimal Blocking – The use of fire‐and‐forget tasks in the workflow helps to immediately persist the entity without waiting on longer processing.

This refactored design separates concerns effectively and “frees” the controllers from excessive business logic while making the system more maintainable and robust.