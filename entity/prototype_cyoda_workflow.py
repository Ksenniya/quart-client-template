Below is one complete solution. In the updated code we define two new “workflow” functions – one for Cyoda Environment deployments and one for User Application deployments. When storing a new deployment record via entity_service.add_item the call now passes the corresponding workflow function as a parameter. (Inside each workflow the entity is simply enriched with a timestamp and a modified status; you can update that logic as needed.) 

Below is the complete updated code:

------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from dataclasses import dataclass
from aiohttp import ClientSession
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring

# New external dependencies for entity service and config
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)  # Registers Quart-Schema for the application

# ------------------------------
# Register startup hook for cyoda initialization
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# ------------------------------
# Dataclasses for Request and Response validation

@dataclass
class CyodaEnvDeployRequest:
    username: str

@dataclass
class CyodaEnvDeployResponse:
    build_id: str
    status: str

# EmptyRequest used for POST endpoints that do not need any request body.
@dataclass
class EmptyRequest:
    pass

@dataclass
class DeploymentStatusResponse:
    build_id: str
    status: str
    details: dict  # TODO: Consider refining the structure if needed.

@dataclass
class DeploymentStatisticsResponse:
    build_id: str
    statistics: dict  # TODO: Consider refining the structure if needed.

@dataclass
class UserAppDeployRequest:
    repository_url: str
    is_public: bool

@dataclass
class UserAppDeployResponse:
    build_id: str
    status: str

@dataclass
class CancelDeploymentRequest:
    comment: str

@dataclass
class CancelDeploymentResponse:
    build_id: str
    status: str
    message: str

# ------------------------------
# Helper function to simulate an external TeamCity API call.
# TODO: Replace simulated response with a real HTTP call if needed.
async def call_teamcity_api(method, url, payload=None):
    async with ClientSession() as session:
        # Simulate delay and return a dummy response.
        await asyncio.sleep(0.5)
        if method.upper() == 'POST':
            return {"buildId": str(uuid.uuid4())}
        elif method.upper() == 'GET':
            # Return a simulated build status or statistics.
            return {"status": "running", "statistics": {"dummy_stat": 123}}
    return {}

# ------------------------------
# Asynchronous task to simulate processing of a build.
# Instead of updating a local dictionary, we fetch, modify, and update the record via entity_service.
async def process_build(build_id, deployment_type, entity_model, username=None, repository_url=None):
    # Get the current record from the external service.
    record = entity_service.get_item(
        token=cyoda_token,
        entity_model=entity_model,
        entity_version=ENTITY_VERSION,
        technical_id=build_id
    )
    if not record:
        return
    # Update status to queued.
    record["status"] = "queued"
    entity_service.update_item(
        token=cyoda_token,
        entity_model=entity_model,
        entity_version=ENTITY_VERSION,
        entity=record,
        meta={}
    )
    await asyncio.sleep(1)  # Simulate delay before running
    # Update status to running.
    record["status"] = "running"
    entity_service.update_item(
        token=cyoda_token,
        entity_model=entity_model,
        entity_version=ENTITY_VERSION,
        entity=record,
        meta={}
    )
    # TODO: Here perform any data processing or calculations required.
    await asyncio.sleep(1)  # Simulate processing time
    # Finally update status to success.
    record["status"] = "success"
    record["finished_at"] = datetime.datetime.utcnow().isoformat()
    # Simulate statistics from an external call.
    record["statistics"] = {"build_time": "2 seconds", "dummy_stat": 123}
    entity_service.update_item(
        token=cyoda_token,
        entity_model=entity_model,
        entity_version=ENTITY_VERSION,
        entity=record,
        meta={}
    )

# ------------------------------
# Workflow functions applied via entity_service.add_item.
# These functions take the validated entity record as input, massage it (e.g. add timestamps)
# or change state before the external service persists them.
def process_cyoda_env_deployment(entity):
    # Add a timestamp indicating workflow processing began.
    entity["workflow_processing_started_at"] = datetime.datetime.utcnow().isoformat()
    # For example, we may want to prefix the status.
    if "status" in entity:
        entity["status"] = "workflow_" + entity["status"]
    return entity

def process_user_app_deployment(entity):
    # Add a timestamp indicating workflow processing began.
    entity["workflow_processing_started_at"] = datetime.datetime.utcnow().isoformat()
    if "status" in entity:
        entity["status"] = "workflow_" + entity["status"]
    return entity

# ------------------------------
# Middleware to check the Bearer token.
async def require_auth():
    auth = request.headers.get("Authorization", None)
    if not auth or not auth.startswith("Bearer "):
        abort(401, description="Missing or invalid Authorization header")
    # TODO: Add actual token validation logic.
    return auth[7:]

# ------------------------------
# Routes for Cyoda Environment Deployment

@app.route('/api/deploy/cyoda-env', methods=['POST'])
@validate_request(CyodaEnvDeployRequest)  # For POST endpoints, must go after route (workaround)
@validate_response(CyodaEnvDeployResponse, 200)
async def deploy_cyoda_env(data: CyodaEnvDeployRequest):
    await require_auth()
    username = data.username
    if not username:
        abort(400, description="username is required")
    payload = {
        "buildType": {"id": "KubernetesPipeline_CyodaSaas"},
        "properties": {
            "property": [
                {"name": "user_defined_keyspace", "value": username},
                {"name": "user_defined_namespace", "value": username}
            ]
        }
    }
    teamcity_response = await call_teamcity_api('POST', 'https://teamcity.cyoda.org/app/rest/buildQueue', payload)
    build_id = teamcity_response.get("buildId", str(uuid.uuid4()))
    # Prepare the deployment record.
    deployment_record = {
        "build_id": build_id,
        "username": username,
        "status": "initiated",
        "requested_at": datetime.datetime.utcnow().isoformat(),
        "statistics": {}
    }
    # Store via external service.
    # Note the workflow parameter with process_cyoda_env_deployment.
    new_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="cyoda_env_deployment",
        entity_version=ENTITY_VERSION,
        entity=deployment_record,
        workflow=process_cyoda_env_deployment
    )
    # For consistency we use the returned id as build_id.
    build_id = new_id
    # Begin asynchronous processing.
    asyncio.create_task(process_build(build_id, deployment_type="cyoda-env", entity_model="cyoda_env_deployment", username=username))
    return jsonify({"build_id": build_id, "status": "initiated"})

@app.route('/api/deploy/cyoda-env/<build_id>/status', methods=['POST'])
@validate_request(EmptyRequest)  # Using EmptyRequest because no body details are needed.
@validate_response(DeploymentStatusResponse, 200)
async def check_cyoda_env_status(build_id, data: EmptyRequest):
    await require_auth()
    # Retrieve the record from the external service.
    deployment_record = entity_service.get_item(
        token=cyoda_token,
        entity_model="cyoda_env_deployment",
        entity_version=ENTITY_VERSION,
        technical_id=build_id
    )
    if not deployment_record:
        abort(404, description="Build not found")
    return jsonify({
        "build_id": build_id,
        "status": deployment_record.get("status"),
        "details": deployment_record
    })

@app.route('/api/deploy/cyoda-env/<build_id>/statistics', methods=['POST'])
@validate_request(EmptyRequest)
@validate_response(DeploymentStatisticsResponse, 200)
async def fetch_cyoda_env_statistics(build_id, data: EmptyRequest):
    await require_auth()
    deployment_record = entity_service.get_item(
        token=cyoda_token,
        entity_model="cyoda_env_deployment",
        entity_version=ENTITY_VERSION,
        technical_id=build_id
    )
    if not deployment_record:
        abort(404, description="Build not found")
    return jsonify({
        "build_id": build_id,
        "statistics": deployment_record.get("statistics", {})
    })

@app.route('/api/deploy/cyoda-env/<build_id>', methods=['GET'])
async def get_cyoda_env_deployment(build_id):
    await require_auth()
    deployment_record = entity_service.get_item(
        token=cyoda_token,
        entity_model="cyoda_env_deployment",
        entity_version=ENTITY_VERSION,
        technical_id=build_id
    )
    if not deployment_record:
        abort(404, description="Build not found")
    return jsonify(deployment_record)

@app.route('/api/deploy/cyoda-env/<build_id>/statistics', methods=['GET'])
async def get_cyoda_env_statistics(build_id):
    await require_auth()
    deployment_record = entity_service.get_item(
        token=cyoda_token,
        entity_model="cyoda_env_deployment",
        entity_version=ENTITY_VERSION,
        technical_id=build_id
    )
    if not deployment_record:
        abort(404, description="Build not found")
    return jsonify({
        "build_id": build_id,
        "statistics": deployment_record.get("statistics", {})
    })

# ------------------------------
# Routes for User Application Deployment

@app.route('/api/deploy/user-app', methods=['POST'])
@validate_request(UserAppDeployRequest)
@validate_response(UserAppDeployResponse, 200)
async def deploy_user_app(data: UserAppDeployRequest):
    await require_auth()
    repository_url = data.repository_url
    is_public = data.is_public
    if not repository_url:
        abort(400, description="repository_url is required")
    # TODO: Validate repository_url format and access.
    username = "extracted-from-token"  # TODO: Replace with actual extraction logic.
    payload = {
        "buildType": {"id": "KubernetesPipeline_CyodaSaasUserEnv"},
        "properties": {
            "property": [
                {"name": "user_defined_keyspace", "value": username},
                {"name": "user_defined_namespace", "value": username}
            ]
        }
    }
    teamcity_response = await call_teamcity_api('POST', 'https://teamcity.cyoda.org/app/rest/buildQueue', payload)
    build_id = teamcity_response.get("buildId", str(uuid.uuid4()))
    deployment_record = {
        "build_id": build_id,
        "username": username,
        "repository_url": repository_url,
        "is_public": is_public,
        "status": "initiated",
        "requested_at": datetime.datetime.utcnow().isoformat(),
        "statistics": {}
    }
    # Store via external service with the user-app deployment workflow.
    new_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="user_app_deployment",
        entity_version=ENTITY_VERSION,
        entity=deployment_record,
        workflow=process_user_app_deployment
    )
    build_id = new_id
    asyncio.create_task(process_build(build_id, deployment_type="user-app", entity_model="user_app_deployment", username=username, repository_url=repository_url))
    return jsonify({"build_id": build_id, "status": "initiated"})

@app.route('/api/deploy/user-app/<build_id>/status', methods=['POST'])
@validate_request(EmptyRequest)
@validate_response(DeploymentStatusResponse, 200)
async def check_user_app_status(build_id, data: EmptyRequest):
    await require_auth()
    deployment_record = entity_service.get_item(
        token=cyoda_token,
        entity_model="user_app_deployment",
        entity_version=ENTITY_VERSION,
        technical_id=build_id
    )
    if not deployment_record:
        abort(404, description="Build not found")
    return jsonify({
        "build_id": build_id,
        "status": deployment_record.get("status"),
        "details": deployment_record
    })

@app.route('/api/deploy/user-app/<build_id>/statistics', methods=['POST'])
@validate_request(EmptyRequest)
@validate_response(DeploymentStatisticsResponse, 200)
async def fetch_user_app_statistics(build_id, data: EmptyRequest):
    await require_auth()
    deployment_record = entity_service.get_item(
        token=cyoda_token,
        entity_model="user_app_deployment",
        entity_version=ENTITY_VERSION,
        technical_id=build_id
    )
    if not deployment_record:
        abort(404, description="Build not found")
    return jsonify({
        "build_id": build_id,
        "statistics": deployment_record.get("statistics", {})
    })

@app.route('/api/deploy/user-app/<build_id>', methods=['GET'])
async def get_user_app_deployment(build_id):
    await require_auth()
    deployment_record = entity_service.get_item(
        token=cyoda_token,
        entity_model="user_app_deployment",
        entity_version=ENTITY_VERSION,
        technical_id=build_id
    )
    if not deployment_record:
        abort(404, description="Build not found")
    return jsonify(deployment_record)

@app.route('/api/deploy/user-app/<build_id>/statistics', methods=['GET'])
async def get_user_app_statistics(build_id):
    await require_auth()
    deployment_record = entity_service.get_item(
        token=cyoda_token,
        entity_model="user_app_deployment",
        entity_version=ENTITY_VERSION,
        technical_id=build_id
    )
    if not deployment_record:
        abort(404, description="Build not found")
    return jsonify({
        "build_id": build_id,
        "statistics": deployment_record.get("statistics", {})
    })

@app.route('/api/deploy/cancel/user-app/<build_id>', methods=['POST'])
@validate_request(CancelDeploymentRequest)
@validate_response(CancelDeploymentResponse, 200)
async def cancel_user_app_deployment(build_id, data: CancelDeploymentRequest):
    await require_auth()
    comment = data.comment if data.comment else "Canceling a queued build"
    deployment_record = entity_service.get_item(
        token=cyoda_token,
        entity_model="user_app_deployment",
        entity_version=ENTITY_VERSION,
        technical_id=build_id
    )
    if not deployment_record:
        abort(404, description="Build not found")
    if deployment_record.get("status") not in ["initiated", "queued", "running"]:
        abort(400, description="Build cannot be canceled")
    payload = {
        "comment": comment,
        "readdIntoQueue": False
    }
    # TODO: Replace with actual cancellation call via aiohttp if needed.
    cancel_response = await call_teamcity_api('POST', f'https://teamcity.cyoda.org/app/rest/builds/id:{build_id}', payload)
    deployment_record["status"] = "canceled"
    deployment_record["canceled_at"] = datetime.datetime.utcnow().isoformat()
    entity_service.update_item(
        token=cyoda_token,
        entity_model="user_app_deployment",
        entity_version=ENTITY_VERSION,
        entity=deployment_record,
        meta={}
    )
    return jsonify({
        "build_id": build_id,
        "status": "canceled",
        "message": "Build cancellation initiated."
    })

# ------------------------------
# Entry Point
if __name__ == '__main__':
    # Run Quart using debug and threaded options.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
------------------------------------------------

Notes:
1. In this version every call to entity_service.add_item passes a workflow function – either process_cyoda_env_deployment or process_user_app_deployment – which are used to adjust the entity before it is persisted.
2. The workflow functions here simply add a workflow processing timestamp and, in this example, prefix the status field. Adjust the logic to suit your actual requirements.
3. All other business logic – calling the TeamCity API, simulated build processing via process_build, request validation, etc. – remains unchanged.

This implementation meets the requirement to update add_item calls with the new workflow function parameter while returning a complete code sample.