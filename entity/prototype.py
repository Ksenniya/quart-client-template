Below is an example prototype.py that implements the API design using Quart and aiohttp. This code uses in‑memory dictionaries as a mock persistence store and simulates external TeamCity calls with asynchronous tasks. Wherever an external call is made or persistence is simulated, a TODO comment is added. This prototype is only a working first pass to validate the UX and identify any additional requirements.

------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from aiohttp import ClientSession
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema

app = Quart(__name__)
QuartSchema(app)  # Registers Quart-Schema for the application

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
    # Should not reach here.
    return {}

# ------------------------------
# Asynchronous task to simulate processing of a build.
async def process_build(deployment_dict, build_id, deployment_type, username=None, repository_url=None):
    # Mark as processing (simulate queued -> running -> completed)
    deployment = deployment_dict.get(build_id)
    if not deployment:
        return
    deployment["status"] = "queued"
    # Save the initial time details if needed.
    await asyncio.sleep(1)  # Simulate delay before running
    deployment["status"] = "running"
    # TODO: Here perform any data processing/calculations required.
    await asyncio.sleep(1)  # Simulate processing time
    # Optionally simulate different outcomes
    deployment["status"] = "success"
    deployment["finished_at"] = datetime.datetime.utcnow().isoformat()
    # Simulate statistics returned by an external call (TeamCity GET)
    deployment["statistics"] = {"build_time": "2 seconds", "dummy_stat": 123}

# ------------------------------
# Middleware to check the Bearer token.
# In a real implementation, extract token and validate.
async def require_auth():
    auth = request.headers.get("Authorization", None)
    if not auth or not auth.startswith("Bearer "):
        abort(401, description="Missing or invalid Authorization header")
    # TODO: Add actual token validation logic.
    token = auth[7:]
    return token

# ------------------------------
# Routes for Cyoda Environment Deployment

@app.route('/api/deploy/cyoda-env', methods=['POST'])
async def deploy_cyoda_env():
    await require_auth()
    data = await request.get_json()
    username = data.get("username")
    if not username:
        abort(400, description="username is required")
    # Prepare payload for TeamCity
    payload = {
        "buildType": {"id": "KubernetesPipeline_CyodaSaas"},
        "properties": {
            "property": [
                {"name": "user_defined_keyspace", "value": username},
                {"name": "user_defined_namespace", "value": username}
            ]
        }
    }
    # Simulate external API call to TeamCity
    # TODO: Uncomment and implement the actual API call with aiohttp if needed.
    teamcity_response = await call_teamcity_api('POST', 'https://teamcity.cyoda.org/app/rest/buildQueue', payload)
    # Generate a build_id if not provided by teamcity_response.
    build_id = teamcity_response.get("buildId", str(uuid.uuid4()))
    # Cache the deployment record.
    deployment_record = {
        "build_id": build_id,
        "username": username,
        "status": "initiated",
        "requested_at": datetime.datetime.utcnow().isoformat(),
        "statistics": {}
    }
    cyoda_env_deployments[build_id] = deployment_record
    # Fire and forget the processing task.
    asyncio.create_task(process_build(cyoda_env_deployments, build_id, deployment_type="cyoda-env", username=username))
    return jsonify({"build_id": build_id, "status": "initiated"})

@app.route('/api/deploy/cyoda-env/<build_id>/status', methods=['POST'])
async def check_cyoda_env_status(build_id):
    await require_auth()
    # TODO: Optionally re-trigger a TeamCity GET call to refresh status.
    # For now, just return the stored status.
    deployment_record = cyoda_env_deployments.get(build_id)
    if not deployment_record:
        abort(404, description="Build not found")
    return jsonify({
        "build_id": build_id,
        "status": deployment_record.get("status"),
        "details": deployment_record
    })

@app.route('/api/deploy/cyoda-env/<build_id>/statistics', methods=['POST'])
async def fetch_cyoda_env_statistics(build_id):
    await require_auth()
    # TODO: Optionally invoke a TeamCity GET to fetch realtime statistics.
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
async def deploy_user_app():
    await require_auth()
    data = await request.get_json()
    repository_url = data.get("repository_url")
    is_public = data.get("is_public")
    if not repository_url:
        abort(400, description="repository_url is required")
    # TODO: Validate repository_url, e.g. ensure valid URL format/repository access.
    # Extract username from token or request (for prototype, we use a fixed value)
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
async def check_user_app_status(build_id):
    await require_auth()
    deployment_record = user_app_deployments.get(build_id)
    if not deployment_record:
        abort(404, description="Build not found")
    # TODO: Optionally trigger a refresh from TeamCity.
    return jsonify({
        "build_id": build_id,
        "status": deployment_record.get("status"),
        "details": deployment_record
    })

@app.route('/api/deploy/user-app/<build_id>/statistics', methods=['POST'])
async def fetch_user_app_statistics(build_id):
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
async def cancel_user_app_deployment(build_id):
    await require_auth()
    data = await request.get_json() or {}
    comment = data.get("comment", "Canceling a queued build")
    deployment_record = user_app_deployments.get(build_id)
    if not deployment_record:
        abort(404, description="Build not found")
    # Check if cancellation is allowed (only cancel if still processing)
    if deployment_record.get("status") not in ["initiated", "queued", "running"]:
        abort(400, description="Build cannot be canceled")
    # Simulate calling TeamCity cancellation endpoint.
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

This sample code covers:
• All endpoints for both Cyoda environment and user application deployments.
• Simulated calls to external TeamCity endpoints using aiohttp.ClientSession.
• In‑memory caches for persistence with fire‐and‐forget processing tasks.
• Simple Bearer token checking (with a TODO for real token validation).

This prototype should serve as a proof-of‑concept to verify the user experience while we refine further functional and non‑functional requirements.