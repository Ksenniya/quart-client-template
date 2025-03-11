import asyncio
import uuid
import logging
from datetime import datetime

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)  # Enable QuartSchema for the application

# In-memory local cache for deployment jobs
deployment_jobs = {}

# TeamCity endpoint configuration (using provided URLs)
TEAMCITY_BUILD_URL = "https://teamcity.cyoda.org/app/rest/buildQueue"
# Note: For status and statistics, we would use endpoints like:
#   GET https://teamcity.cyoda.org/app/rest/buildQueue/id:{build_id}
#   GET https://teamcity.cyoda.org/app/rest/builds/id:{build_id}/statistics/
# Here we simulate the responses.

async def trigger_teamcity_build(build_type: str, properties: dict) -> str:
    """
    Triggers a build in TeamCity given a build type and properties.
    Uses httpx.AsyncClient to perform a POST request.
    If failure occurs, logs error and simulates a build_id.
    """
    payload = {
        "buildType": {"id": build_type},
        "properties": {"property": []},
    }
    for key, value in properties.items():
        payload["properties"]["property"].append({"name": key, "value": value})
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(TEAMCITY_BUILD_URL, json=payload, timeout=10.0)
            response.raise_for_status()
            resp_json = response.json()
            # Assume response returns a build_id, otherwise simulate one.
            build_id = resp_json.get("build_id", str(uuid.uuid4()))
            return build_id
        except Exception as e:
            logger.exception(e)
            # TODO: Replace simulation with proper error handling/retry logic
            return str(uuid.uuid4())

async def process_deployment(job_id: str, payload: dict):
    """
    Simulates the processing of a deployment job.
    This function would poll external systems (TeamCity)
    for build status and update job statistics accordingly.
    """
    try:
        # Simulate build processing time
        await asyncio.sleep(2)  # simulate deployment time
        # TODO: Implement proper polling of TeamCity APIs to obtain actual status
        deployment_jobs[job_id]["status"] = "completed"
        deployment_jobs[job_id]["statistics"] = {
            "duration": "2s",
            "success": True
        }
        logger.info(f"Deployment job {job_id} completed.")
    except Exception as e:
        logger.exception(e)
        deployment_jobs[job_id]["status"] = "failed"
        deployment_jobs[job_id]["statistics"] = {
            "duration": "2s",
            "success": False
        }

@app.route("/deploy/cyoda-env", methods=["POST"])
async def deploy_cyoda_env():
    """
    Deploys a Cyoda environment based on a provided user_name.
    Triggers a TeamCity build and returns a build_id.
    """
    data = await request.get_json()
    user_name = data.get("user_name")
    if not user_name:
        return jsonify({"error": "user_name is required"}), 400

    build_type = "KubernetesPipeline_CyodaSaas"
    properties = {
        "user_defined_keyspace": user_name,
        "user_defined_namespace": user_name
    }
    build_id = await trigger_teamcity_build(build_type, properties)

    # Store job status in local cache with a timestamp
    deployment_jobs[build_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat()
    }

    # Fire and forget the asynchronous processing task.
    asyncio.create_task(process_deployment(build_id, data))

    return jsonify({"build_id": build_id}), 201

@app.route("/deploy/user_app", methods=["POST"])
async def deploy_user_app():
    """
    Deploys a user application using repository URL and user_name.
    Invokes the TeamCity build and returns a build_id.
    """
    data = await request.get_json()
    repository_url = data.get("repository_url")
    user_name = data.get("user_name")
    if not repository_url or not user_name:
        return jsonify({"error": "repository_url and user_name are required"}), 400

    build_type = "KubernetesPipeline_CyodaSaasUserEnv"
    properties = {
        "repository_url": repository_url,  # TODO: Verify if this should use repository_url or another parameter
        "user_defined_namespace": user_name
    }
    build_id = await trigger_teamcity_build(build_type, properties)

    deployment_jobs[build_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat()
    }

    asyncio.create_task(process_deployment(build_id, data))

    return jsonify({"build_id": build_id}), 201

@app.route("/deploy/cyoda-env/status/<string:build_id>", methods=["GET"])
async def get_cyoda_env_status(build_id):
    """
    Retrieves the status of a Cyoda environment deployment.
    """
    job = deployment_jobs.get(build_id)
    if not job:
        return jsonify({"error": "build_id not found"}), 404

    status_message = "Deployment is currently running." if job["status"] == "processing" else "Deployment completed."
    return jsonify({
        "status": job["status"],
        "details": status_message
    })

@app.route("/deploy/cyoda-env/statistics/<string:build_id>", methods=["GET"])
async def get_cyoda_env_statistics(build_id):
    """
    Retrieves deployment statistics for a Cyoda environment.
    """
    job = deployment_jobs.get(build_id)
    if not job or "statistics" not in job:
        return jsonify({"error": "statistics not available"}), 404
    return jsonify(job["statistics"])

@app.route("/deploy/user_app/status/<string:build_id>", methods=["GET"])
async def get_user_app_status(build_id):
    """
    Retrieves the status of a user application deployment.
    """
    job = deployment_jobs.get(build_id)
    if not job:
        return jsonify({"error": "build_id not found"}), 404

    status_message = "Deployment is currently running." if job["status"] == "processing" else "Deployment completed."
    return jsonify({
        "status": job["status"],
        "details": status_message
    })

@app.route("/deploy/user_app/statistics/<string:build_id>", methods=["GET"])
async def get_user_app_statistics(build_id):
    """
    Retrieves deployment statistics for a user application.
    """
    job = deployment_jobs.get(build_id)
    if not job or "statistics" not in job:
        return jsonify({"error": "statistics not available"}), 404
    return jsonify(job["statistics"])

@app.route("/deploy/cancel/user_app/<string:build_id>", methods=["POST"])
async def cancel_user_app_deployment(build_id):
    """
    Cancels an ongoing user application deployment.
    """
    data = await request.get_json()
    job = deployment_jobs.get(build_id)
    if not job:
        return jsonify({"error": "build_id not found"}), 404

    # TODO: If supported, invoke the TeamCity API to cancel the build.
    job["status"] = "canceled"
    return jsonify({"message": "Deployment canceled successfully."})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)