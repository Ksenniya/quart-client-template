from quart import Quart, request, jsonify
from quart_schema import QuartSchema
from app_init.app_init import entity_service
import uuid

app = Quart(__name__)
QuartSchema(app)

user_apps_cache = {}

token = "your_token_here"
ENTITY_VERSION = "1.0"

@app.route('/deploy/environments', methods=['POST'])
async def create_environment():
    data = await request.get_json()
    result = await entity_service.add_item(
        token=token,
        entity_model="environments",
        entity_version=ENTITY_VERSION,
        entity=data,
    )
    return jsonify(result)

@app.route('/deploy/user-apps', methods=['POST'])
async def deploy_user_app():
    data = await request.get_json()
    result = await entity_service.add_item(
        token=token,
        entity_model="user_apps",
        entity_version=ENTITY_VERSION,
        entity=data,
    )
    return jsonify(result)

@app.route('/deploy/environments/<id>/status', methods=['GET'])
async def get_environment_status(id):
    result = await entity_service.get_item(
        token=token,
        entity_model="environments",
        entity_version=ENTITY_VERSION,
        technical_id=id,
    )
    if result:
        return jsonify(result)
    return jsonify({'error': 'Not found'}), 404

@app.route('/deploy/environments/<id>/statistics', methods=['GET'])
async def get_environment_statistics(id):
    result = await entity_service.get_item(
        token=token,
        entity_model="environments",
        entity_version=ENTITY_VERSION,
        technical_id=id,
    )
    if result:
        return jsonify(result)
    return jsonify({'error': 'Not found'}), 404

@app.route('/deploy/user-apps/<id>/cancel', methods=['POST'])
async def cancel_user_app(id):
    user_app = user_apps_cache.get(id)
    if user_app:
        user_apps_cache.pop(id)
        return jsonify({'message': 'Build canceled successfully'})
    return jsonify({'error': 'Not found'}), 404

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)