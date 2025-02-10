# ```python
from quart import Blueprint, request, jsonify
from common.service.entity_service_interface import EntityService  # Assuming you have an implementation of this class
import aiohttp

api_bp_env_deployment = Blueprint('api/env_deployment', __name__)

ENTITY_VERSION = '1.0'  # Change this as needed
CYODA_TOKEN = 'Your_Cyoda_Token'  # Replace with your actual token

@api_bp_env_deployment.route('/deploy/cyoda-env', methods=['POST'])
async def initiate_deployment():
    data = await request.get_json()
    entity_id = await entity_service.add_item(CYODA_TOKEN, 'env_deployment', ENTITY_VERSION, data)
    return jsonify({'entity_id': entity_id}), 201

@api_bp_env_deployment.route('/deploy/cyoda-env/status/<string:build_id>', methods=['GET'])
async def get_deployment_status(build_id):
    entity_data = await entity_service.get_item(CYODA_TOKEN, 'env_deployment', ENTITY_VERSION, build_id)
    return jsonify(entity_data), 200

@api_bp_env_deployment.route('/deploy/cyoda-env/statistics/<string:build_id>', methods=['GET'])
async def get_deployment_statistics(build_id):
    entity_data = await entity_service.get_item(CYODA_TOKEN, 'env_deployment', ENTITY_VERSION, build_id)
    # Assuming statistics can be derived or is part of the entity_data
    return jsonify(entity_data), 200
# ```