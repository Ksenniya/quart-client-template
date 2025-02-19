from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import aiohttp
from app_init.app_init import entity_service

app = Quart(__name__)
QuartSchema(app)

@app.route('/auth', methods=['POST'])
async def authenticate():
    data = await request.get_json()
    if "token" in data:
        return jsonify({"status": "authenticated"}), 200
    return jsonify({"error": "Invalid token"}), 401

@app.route('/environments', methods=['POST'])
async def create_environment():
    data = await request.get_json()
    user_name = data.get("user_name")
    environments = await entity_service.get_items(
        token=token,
        entity_model="environments",
        entity_version=ENTITY_VERSION
    )
    build_id = f"env_build_{len(environments) + 1}"
    new_environment = {"build_id": build_id, "user_name": user_name, "status": "pending"}
    await entity_service.add_item(
        token=token,
        entity_model="environments",
        entity_version=ENTITY_VERSION,
        entity=new_environment
    )
    async with aiohttp.ClientSession() as session:
        await session.post("https://teamcity.cyoda.org/app/rest/buildQueue", json={
            "buildType": {"id": "KubernetesPipeline_CyodaSaas"},
            "properties": {"property": [
                {"name": "user_defined_keyspace", "value": user_name},
                {"name": "user_defined_namespace", "value": user_name}
            ]}
        })
    return jsonify({"build_id": build_id}), 201

@app.route('/environments/<string:id>/status', methods=['GET'])
async def get_environment_status(id):
    environment = await entity_service.get_item(
        token=token,
        entity_model="environments",
        entity_version=ENTITY_VERSION,
        technical_id=id
    )
    if environment:
        return jsonify({"status": environment["status"], "details": "..."})
    return jsonify({"error": "Environment not found"}), 404

@app.route('/environments/<string:id>/statistics', methods=['GET'])
async def get_environment_statistics(id):
    return jsonify({"statistics": {"duration": "10s", "success_rate": "100%"}})

@app.route('/user-apps', methods=['POST'])
async def create_user_app():
    data = await request.get_json()
    repository_url = data.get("repository_url")
    is_public = data.get("is_public")
    user_apps = await entity_service.get_items(
        token=token,
        entity_model="user_apps",
        entity_version=ENTITY_VERSION
    )
    build_id = f"user_app_build_{len(user_apps) + 1}"
    new_user_app = {
        "build_id": build_id,
        "repository_url": repository_url,
        "is_public": is_public,
        "status": "pending"
    }
    await entity_service.add_item(
        token=token,
        entity_model="user_apps",
        entity_version=ENTITY_VERSION,
        entity=new_user_app
    )
    async with aiohttp.ClientSession() as session:
        await session.post("https://teamcity.cyoda.org/app/rest/buildQueue", json={
            "buildType": {"id": "KubernetesPipeline_CyodaSaasUserEnv"},
            "properties": {"property": [
                {"name": "user_defined_keyspace", "value": "TODO"},
                {"name": "user_defined_namespace", "value": "TODO"}
            ]}
        })
    return jsonify({"build_id": build_id}), 201

@app.route('/user-apps/<string:id>/status', methods=['GET'])
async def get_user_app_status(id):
    user_app = await entity_service.get_item(
        token=token,
        entity_model="user_apps",
        entity_version=ENTITY_VERSION,
        technical_id=id
    )
    if user_app:
        return jsonify({"status": user_app["status"], "details": "..."})
    return jsonify({"error": "User app not found"}), 404

@app.route('/user-apps/<string:id>/statistics', methods=['GET'])
async def get_user_app_statistics(id):
    return jsonify({"statistics": {"duration": "10s", "success_rate": "100%"}})

@app.route('/user-apps/<string:id>/cancel', methods=['POST'])
async def cancel_user_app(id):
    user_app = await entity_service.get_item(
        token=token,
        entity_model="user_apps",
        entity_version=ENTITY_VERSION,
        technical_id=id
    )
    if user_app:
        return jsonify({"status": "canceled"}), 200
    return jsonify({"error": "User app not found"}), 404

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)