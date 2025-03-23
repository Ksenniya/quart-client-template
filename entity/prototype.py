```python
import asyncio
import logging
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

app = Quart(__name__)
QuartSchema(app)

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Local cache for job persistence
entity_job = {}

# External API URL
TEAMCITY_API_URL = "https://teamcity.test/app/rest"

@dataclass
class DeployCyodaEnvRequest:
    user_name: str

@dataclass
class DeployUserAppRequest:
    repository_url: str
    is_public: bool
    user_name: str

@dataclass
class CancelUserAppRequest:
    comment: str
    readdIntoQueue: bool

async def trigger_teamcity_build(build_type_id, properties):
    """Trigger a build on TeamCity."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{TEAMCITY_API_URL}/buildQueue",
            json={
                "buildType": {"id": build_type_id},
                "properties": {"property": properties}
            }
        )
        response.raise_for_status()
        return response.json()  # Return the response JSON

@app.route('/deploy/cyoda-env', methods=['POST'])
@validate_request(DeployCyodaEnvRequest)  # Validation last for POST
async def deploy_cyoda_env(data: DeployCyodaEnvRequest):
    user_name = data.user_name
    
    # Prepare properties for TeamCity
    properties = [
        {"name": "user_defined_keyspace", "value": user_name},
        {"name": "user_defined_namespace", "value": user_name}
    ]

    # Trigger the build
    build_response = await trigger_teamcity_build("KubernetesPipeline_CyodaSaas", properties)
    build_id = build_response.get("id")  # Assuming the build response has an 'id' field

    # Store job information
    entity_job[build_id] = {"status": "queued", "requestedAt": asyncio.get_event_loop().time()}
    
    return jsonify({"build_id": build_id, "status": "queued"})

@app.route('/deploy/user_app', methods=['POST'])
@validate_request(DeployUserAppRequest)  # Validation last for POST
async def deploy_user_app(data: DeployUserAppRequest):
    repository_url = data.repository_url
    user_name = data.user_name

    # Prepare properties for TeamCity
    properties = [
        {"name": "repository_url", "value": repository_url},
        {"name": "user_defined_namespace", "value": user_name}
    ]

    # Trigger the build
    build_response = await trigger_teamcity_build("KubernetesPipeline_CyodaSaasUserEnv", properties)
    build_id = build_response.get("id")  # Assuming the build response has an 'id' field

    # Store job information
    entity_job[build_id] = {"status": "queued", "requestedAt": asyncio.get_event_loop().time()}
    
    return jsonify({"build_id": build_id, "status": "queued"})

@app.route('/deploy/cyoda-env/status/<string:build_id>', methods=['GET'])
async def get_cyoda_env_status(build_id):
    # TODO: Implement the logic to get the build status from TeamCity
    # Mock response for demonstration
    job = entity_job.get(build_id, None)
    if job:
        return jsonify({"build_id": build_id, "status": job["status"], "details": "Deployment in progress..."})
    return jsonify({"error": "Build ID not found"}), 404

@app.route('/deploy/user_app/status/<string:build_id>', methods=['GET'])
async def get_user_app_status(build_id):
    # TODO: Implement the logic to get the build status from TeamCity
    # Mock response for demonstration
    job = entity_job.get(build_id, None)
    if job:
        return jsonify({"build_id": build_id, "status": job["status"], "details": "Deployment in progress..."})
    return jsonify({"error": "Build ID not found"}), 404

@app.route('/deploy/cancel/user_app/<string:build_id>', methods=['POST'])
@validate_request(CancelUserAppRequest)  # Validation last for POST
async def cancel_user_app(data: CancelUserAppRequest, build_id: str):
    # TODO: Implement the logic to cancel the build in TeamCity
    # Mock response for demonstration
    job = entity_job.pop(build_id, None)
    if job:
        return jsonify({"build_id": build_id, "status": "canceled"})
    return jsonify({"error": "Build ID not found"}), 404

if __name__ == '__main__':
