from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import aiohttp
from app_init.app_init import entity_service

app = Quart(__name__)
QuartSchema(app)

TEAMCITY_API_URL = "https://teamcity.cyoda.org/app/rest/buildQueue"
ENTITY_VERSION = "1.0"
token = "your_bearer_token"

@app.route('/auth/token', methods=['POST'])
async def authenticate():
    data = await request.get_json()
    return jsonify({"token": token})

@app.route('/deploy/environments', methods=['POST'])
async def create_environment():
    data = await request.get_json()
    env_result = await entity_service.add_item(
        token=token,
        entity_model="environments",
        entity_version=ENTITY_VERSION,
        entity=data
    )
    async with aiohttp.ClientSession() as session:
        async with session.post(TEAMCITY_API_URL, json={
            "buildType": {"id": "KubernetesPipeline_CyodaSaas"},
            "properties": {
                "property": [
                    {"name": "user_defined_keyspace", "value": data.get("user_name")},
                    {"name": "user_defined_namespace", "value": data.get("user_name")}
                ]
            }
        }) as response:
            await response.text()
    return jsonify(env_result)

@app.route('/deploy/environments/<build_id>/status', methods=['GET'])
async def get_environment_status(build_id):
    env_result = await entity_service.get_item(
        token=token,
        entity_model="environments",
        entity_version=ENTITY_VERSION,
        technical_id=build_id
    )
    return jsonify(env_result)

@app.route('/deploy/environments/<build_id>/statistics', methods=['GET'])
async def get_environment_statistics(build_id):
    statistics = {"build_id": build_id, "duration": "10m", "success": True}
    return jsonify(statistics)

@app.route('/deploy/user-apps', methods=['POST'])
async def deploy_user_app():
    data = await request.get_json()
    app_result = await entity_service.add_item(
        token=token,
        entity_model="user_apps",
        entity_version=ENTITY_VERSION,
        entity=data
    )
    async with aiohttp.ClientSession() as session:
        async with session.post(TEAMCITY_API_URL, json={
            "buildType": {"id": "KubernetesPipeline_CyodaSaasUserEnv"},
            "properties": {
                "property": [
                    {"name": "user_defined_keyspace", "value": "example_keyspace"},
                    {"name": "user_defined_namespace", "value": "example_namespace"}
                ]
            }
        }) as response:
            await response.text()
    return jsonify(app_result)

@app.route('/deploy/user-apps/<build_id>/status', methods=['GET'])
async def get_user_app_status(build_id):
    app_result = await entity_service.get_item(
        token=token,
        entity_model="user_apps",
        entity_version=ENTITY_VERSION,
        technical_id=build_id
    )
    return jsonify(app_result)

@app.route('/deploy/user-apps/<build_id>/statistics', methods=['GET'])
async def get_user_app_statistics(build_id):
    statistics = {"build_id": build_id, "duration": "15m", "success": False}
    return jsonify(statistics)

@app.route('/deploy/user-apps/<build_id>/cancel', methods=['POST'])
async def cancel_user_app(build_id):
    from app_init.app_init import entity_service
    result = await entity_service.get_item(
        token=token,
        entity_model="user_apps",
        entity_version=ENTITY_VERSION,
        technical_id=build_id
    )
    if result:
        result["status"] = "canceled"
        return jsonify({"message": "Build canceled successfully."})
    else:
        return jsonify({"message": "Build not found."}), 404

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)