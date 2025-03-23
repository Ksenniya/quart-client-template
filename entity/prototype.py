```python
import asyncio
import logging
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
import httpx

app = Quart(__name__)
QuartSchema(app)

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Local cache to simulate persistence
entity_jobs = {}

# Helper function to trigger TeamCity builds
async def trigger_teamcity_build(build_type_id, properties):
    url = "https://teamcity.test/app/rest/buildQueue"
    payload = {
        "buildType": {"id": build_type_id},
        "properties": {"property": [{"name": k, "value": v} for k, v in properties.items()]}
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()  # Raise an error for HTTP errors
        return response.json()  # Return the response JSON

@dataclass
class CyodaEnvRequest:
    user_name: str

@dataclass
class UserAppRequest:
    repository_url: str
    is_public: bool
    user_name: str

@dataclass
class CancelRequest:
    comment: str
    readdIntoQueue: bool

@app.route('/deploy/cyoda-env', methods=['POST'])
@validate_request(CyodaEnvRequest)  # Validation should be last for POST requests
async def deploy_cyoda_env(data: CyodaEnvRequest):
    user_name = data.user_name
    
    requested_at = asyncio.get_event_loop().time()
    job_id = f"cyoda-{user_name}-{requested_at}"
    
    properties = {
        "user_defined_keyspace": user_name,
        "user_defined_namespace": user_name,
    }
    
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}
    
    try:
        build_response = await trigger_teamcity_build("KubernetesPipeline_CyodaSaas", properties)
        entity_jobs[job_id]["build_id"] = build_response.get("id")
        entity_jobs[job_id]["status"] = "queued"
    except Exception as e:
        logger.exception(e)
        entity_jobs[job_id]["status"] = "failed"
    
    return jsonify({"build_id": entity_jobs[job_id]["build_id"], "status": entity_jobs[job_id]["status"]}), 200

@app.route('/deploy/user_app', methods=['POST'])
@validate_request(UserAppRequest)  # Validation should be last for POST requests
async def deploy_user_app(data: UserAppRequest):
    repository_url = data.repository_url
    is_public = data.is_public
    user_name = data.user_name
    
    requested_at = asyncio.get_event_loop().time()
    job_id = f"user-app-{user_name}-{requested_at}"
    
    properties = {
        "repository_url": repository_url,
        "user_defined_namespace": user_name,
    }
    
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}
    
    try:
        build_response = await trigger_teamcity_build("KubernetesPipeline_CyodaSaasUserEnv", properties)
        entity_jobs[job_id]["build_id"] = build_response.get("id")
        entity_jobs[job_id]["status"] = "queued"
    except Exception as e:
        logger.exception(e)
        entity_jobs[job_id]["status"] = "failed"
    
    return jsonify({"build_id": entity_jobs[job_id]["build_id"], "status": entity_jobs[job_id]["status"]}), 200

@app.route('/deploy/cyoda-env/status/<job_id>', methods=['GET'])
async def get_cyoda_env_status(job_id):
    job = entity_jobs.get(job_id)
    if job:
        return jsonify({"build_id": job.get("build_id"), "status": job.get("status")}), 200
    return jsonify({"error": "Job not found"}), 404

@app.route('/deploy/user_app/status/<job_id>', methods=['GET'])
async def get_user_app_status(job_id):
    job = entity_jobs.get(job_id)
    if job:
        return jsonify({"build_id": job.get("build_id"), "status": job.get("status")}), 200
    return jsonify({"error": "Job not found"}), 404

@app.route('/deploy/cancel/user_app/<job_id>', methods=['POST'])
@validate_request(CancelRequest)  # Validation should be last for POST requests
async def cancel_user_app(data: CancelRequest, job_id):
    job = entity_jobs.get(job_id)
    if job:
        # Here we would cancel the build in TeamCity (not implemented)
        # TODO: Implement the actual cancellation logic