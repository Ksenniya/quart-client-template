from quart import Quart, request, jsonify
from quart_schema import QuartSchema
from app_init.app_init import entity_service

app = Quart(__name__)
QuartSchema(app)

@app.route('/auth/login', methods=['POST'])
async def login():
    data = await request.json
    return jsonify({"token": "Bearer mock_token"})

@app.route('/environments', methods=['POST'])
async def create_environment():
    data = await request.json
    result = await entity_service.add_item(
        token=token,
        entity_model="environments",
        entity_version=ENTITY_VERSION,
        entity=data
    )
    return jsonify(result)

@app.route('/environments/<int:id>/status', methods=['GET'])
async def get_environment_status(id):
    result = await entity_service.get_item(
        token=token,
        entity_model="environments",
        entity_version=ENTITY_VERSION,
        technical_id=id
    )
    return jsonify(result)

@app.route('/environments/<int:id>/statistics', methods=['GET'])
async def get_environment_statistics(id):
    result = await entity_service.get_item(
        token=token,
        entity_model="environments",
        entity_version=ENTITY_VERSION,
        technical_id=id
    )
    return jsonify(result)

@app.route('/user-apps', methods=['POST'])
async def create_user_app():
    data = await request.json
    result = await entity_service.add_item(
        token=token,
        entity_model="user-apps",
        entity_version=ENTITY_VERSION,
        entity=data
    )
    return jsonify(result)

@app.route('/user-apps/<int:id>/status', methods=['GET'])
async def get_user_app_status(id):
    result = await entity_service.get_item(
        token=token,
        entity_model="user-apps",
        entity_version=ENTITY_VERSION,
        technical_id=id
    )
    return jsonify(result)

@app.route('/user-apps/<int:id>/statistics', methods=['GET'])
async def get_user_app_statistics(id):
    result = await entity_service.get_item(
        token=token,
        entity_model="user-apps",
        entity_version=ENTITY_VERSION,
        technical_id=id
    )
    return jsonify(result)

@app.route('/user-apps/<int:id>', methods=['DELETE'])
async def cancel_user_app(id):
    return jsonify({"message": "Not Implemented"}), 501

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)