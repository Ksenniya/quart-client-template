from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response
from aiohttp import ClientSession
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)

ENTITY_VERSION = "1.0"

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@dataclass
class AuthRequest:
    username: str
    password: str

@dataclass
class AuthResponse:
    token: str

@dataclass
class CreateEnvironmentRequest:
    user_name: str

@dataclass
class EnvironmentResponse:
    build_id: int

@dataclass
class CreateUserAppRequest:
    repository_url: str
    is_public: bool

@dataclass
class UserAppResponse:
    build_id: int

@dataclass
class CancelUserAppRequest:
    comment: str
    readdIntoQueue: bool

@dataclass
class CancelUserAppResponse:
    message: str

TEAMCITY_URL = "https://teamcity.cyoda.org/app/rest/buildQueue"

@app.route('/auth', methods=['POST'])
@validate_request(AuthRequest)
@validate_response(AuthResponse, 200)
async def authenticate(data: AuthRequest):
    return AuthResponse(token="mock_bearer_token")

@app.route('/environments', methods=['POST'])
@validate_request(CreateEnvironmentRequest)
@validate_response(EnvironmentResponse, 201)
async def create_environment(data: CreateEnvironmentRequest):
    env_data = {"user_name": data.user_name, "status": "in-progress"}
    saved_env = await entity_service.add_item(
        token=cyoda_token,
        entity_model="environments",
        entity_version=ENTITY_VERSION,
        entity=env_data
    )
    async with ClientSession() as session:
        payload = {
            "buildType": {
                "id": "KubernetesPipeline_CyodaSaas"
            },
            "properties": {
                "property": [
                    {"name": "user_defined_keyspace", "value": data.user_name},
                    {"name": "user_defined_namespace", "value": data.user_name}
                ]
            }
        }
        async with session.post(TEAMCITY_URL, json=payload) as resp:
            await resp.text()
    return EnvironmentResponse(build_id=saved_env["technical_id"])

@app.route('/environments/<int:id>/status', methods=['GET'])
async def get_environment_status(id: int):
    environment = await entity_service.get_item(
        token=cyoda_token,
        entity_model="environments",
        entity_version=ENTITY_VERSION,
        technical_id=id
    )
    if environment:
        return jsonify({"status": environment["status"], "details": "Building..."})
    return jsonify({"error": "Environment not found"}), 404

@app.route('/environments/<int:id>/statistics', methods=['GET'])
async def get_environment_statistics(id: int):
    environment = await entity_service.get_item(
        token=cyoda_token,
        entity_model="environments",
        entity_version=ENTITY_VERSION,
        technical_id=id
    )
    if environment:
        return jsonify({"build_time": "5m", "success_rate": "95%"})
    return jsonify({"error": "Environment not found"}), 404

@app.route('/user-apps', methods=['POST'])
@validate_request(CreateUserAppRequest)
@validate_response(UserAppResponse, 201)
async def create_user_app(data: CreateUserAppRequest):
    app_data = {"repository_url": data.repository_url, "is_public": data.is_public, "status": "in-progress"}
    saved_app = await entity_service.add_item(
        token=cyoda_token,
        entity_model="user_apps",
        entity_version=ENTITY_VERSION,
        entity=app_data
    )
    async with ClientSession() as session:
        payload = {
            "buildType": {
                "id": "KubernetesPipeline_CyodaSaasUserEnv"
            },
            "properties": {
                "property": [
                    {"name": "user_defined_keyspace", "value": "mock_keyspace"},
                    {"name": "user_defined_namespace", "value": "mock_namespace"}
                ]
            }
        }
        async with session.post(TEAMCITY_URL, json=payload) as resp:
            await resp.text()
    return UserAppResponse(build_id=saved_app["technical_id"])

@app.route('/user-apps/<int:id>/status', methods=['GET'])
async def get_user_app_status(id: int):
    user_app = await entity_service.get_item(
        token=cyoda_token,
        entity_model="user_apps",
        entity_version=ENTITY_VERSION,
        technical_id=id
    )
    if user_app:
        return jsonify({"status": user_app["status"], "details": "Deployment successful."})
    return jsonify({"error": "User app not found"}), 404

@app.route('/user-apps/<int:id>/statistics', methods=['GET'])
async def get_user_app_statistics(id: int):
    user_app = await entity_service.get_item(
        token=cyoda_token,
        entity_model="user_apps",
        entity_version=ENTITY_VERSION,
        technical_id=id
    )
    if user_app:
        return jsonify({"build_time": "3m", "success_rate": "90%"})
    return jsonify({"error": "User app not found"}), 404

@app.route('/user-apps/<int:id>', methods=['DELETE'])
@validate_request(CancelUserAppRequest)
@validate_response(CancelUserAppResponse, 200)
async def cancel_user_app(id: int, data: CancelUserAppRequest):
    result = await entity_service.delete_item(
        token=cyoda_token,
        entity_model="user_apps",
        entity_version=ENTITY_VERSION,
        entity={"technical_id": id},
        meta={}
    )
    if result:
        return CancelUserAppResponse(message="Build canceled successfully.")
    return jsonify({"error": "User app not found"}), 404

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)