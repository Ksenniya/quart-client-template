Below is the updated prototype.py with Quart‐Schema validation decorators added. Note that for POST endpoints the decorators are placed in the order required by the library (route first, then validate_request, then validate_response), while for GET endpoints with query parameters (none in our case) the order would be reversed. Comments mark our workaround for this known issue.

------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from dataclasses import dataclass
from aiohttp import ClientSession
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring

app = Quart(__name__)
QuartSchema(app)  # Registers Quart-Schema for the application

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
# In‑memory storage for deployments (mock persistence)
cyoda_env_deployments = {}
user_app_deployments = {}

# ------------------------------
# Helper function to simulate an external TeamCity API call.
# TODO: Replace simulated response with a real HTTP call if needed.
async def call_teamcity_api(method, url, payload=None):
    async with ClientSession() as session:
        # TODO: Implement actual external API call using session.request(...)
        # For now, simulate a delay and return a dummy response.
        await asyncio.sleep(0.5)
        if method.upper() == 'POST':
            return {"buildId": str(uuid.uuid4())}
        elif method.upper() == 'GET':
            # Return a simulated build status or statistics
            return {"status": "running", "statistics": {"dummy_stat": 123}}
    return {}

# ------------------------------
# Asynchronous task to simulate processing of a build.
async def process_build(deployment_dict, build_id, deployment_type, username=None, repository_url=None):
    deployment = deployment_dict.get(build_id)
    if not deployment:
        return
    deployment["status"] = "queued"
    await asyncio.sleep(1)  # Simulate delay before running
    deployment["status"] = "running"
    # TODO: Here perform any data processing/calculations required.
    await asyncio.sleep(1)  # Simulate processing time
    deployment["status"] = "success"
    deployment["finished_at"] = datetime.datetime.utcnow().isoformat()
    # Simulate statistics from an external call
    deployment["statistics"] = {"build_time": "2 seconds", "dummy_stat": 123}

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
    deployment_record = {
        "build_id": build_id,
        "username": username,
        "status": "initiated",
        "requested_at": datetime.datetime.utcnow().isoformat(),
        "statistics": {}
    }
    cyoda_env_deployments[build_id] = deployment_record
    asyncio.create_task(process_build(cyoda_env_deployments, build_id, deployment_type="cyoda-env", username=username))
    return jsonify({"build_id": build_id, "status": "initiated"})

@app.route('/api/deploy/cyoda-env/<build_id>/status', methods=['POST'])
@validate_request(EmptyRequest)  # Using EmptyRequest because no body details are needed.
@validate_response(DeploymentStatusResponse, 200)
async def check_cyoda_env_status(build_id, data: EmptyRequest):
    await require_auth()
    deployment_record = cyoda_env_deployments.get(build_id)
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
    deployment_record = cyoda_env_deployments.get(build_id)
    if not deployment_record:
        abort(404, description="Build not found")
    return jsonify({
        "build_id": build_id,
        "statistics": deployment_record.get("statistics", {})
    })

@app.route('/api/deploy/cyoda-env/<build_id>', methods=['GET'])
async def get_cyoda_env_deployment(build_id):
    await require_auth()
    deployment_record = cyoda_env_deployments.get(build_id)
    if not deployment_record:
        abort(404, description="Build not found")
    return jsonify(deployment_record)

@app.route('/api/deploy/cyoda-env/<build_id>/statistics', methods=['GET'])
async def get_cyoda_env_statistics(build_id):
    await require_auth()
    deployment_record = cyoda_env_deployments.get(build_id)
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
    user_app_deployments[build_id] = deployment_record
    asyncio.create_task(process_build(user_app_deployments, build_id, deployment_type="user-app", username=username, repository_url=repository_url))
    return jsonify({"build_id": build_id, "status": "initiated"})

@app.route('/api/deploy/user-app/<build_id>/status', methods=['POST'])
@validate_request(EmptyRequest)
@validate_response(DeploymentStatusResponse, 200)
async def check_user_app_status(build_id, data: EmptyRequest):
    await require_auth()
    deployment_record = user_app_deployments.get(build_id)
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
    deployment_record = user_app_deployments.get(build_id)
    if not deployment_record:
        abort(404, description="Build not found")
    return jsonify({
        "build_id": build_id,
        "statistics": deployment_record.get("statistics", {})
    })

@app.route('/api/deploy/user-app/<build_id>', methods=['GET'])
async def get_user_app_deployment(build_id):
    await require_auth()
    deployment_record = user_app_deployments.get(build_id)
    if not deployment_record:
        abort(404, description="Build not found")
    return jsonify(deployment_record)

@app.route('/api/deploy/user-app/<build_id>/statistics', methods=['GET'])
async def get_user_app_statistics(build_id):
    await require_auth()
    deployment_record = user_app_deployments.get(build_id)
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
    deployment_record = user_app_deployments.get(build_id)
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
• For GET endpoints we did not add validation because GET requests without query parameters should not use @validate_request.
• For POST endpoints the ordering is: @app.route first, then @validate_request, then @validate_response. This is a workaround for an issue in Quart-Schema.
• Mocks (e.g., call_teamcity_api and in‑memory dictionaries) and TODO comments indicate where real implementations need to be added.

This prototype should help verify the user experience while identifying any gaps in the requirements.