# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION

api_bp_cyoda_env = Blueprint('api/cyoda_env', __name__)

@api_bp_cyoda_env.route('/deploy/cyoda-env', methods=['POST'])
async def add_cyoda_env():
    """API endpoint to deploy a Cyoda environment."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Deploy the Cyoda environment using the entity service
        cyoda_env_id = await entity_service.add_item(
            cyoda_token, 'cyoda_env', ENTITY_VERSION, data
        )
        return jsonify({"cyoda_env_id": cyoda_env_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_cyoda_env.route('/deploy/cyoda-env/status/<int:id>', methods=['GET'])
async def get_cyoda_env_status(id):
    """API endpoint to get the deployment status of Cyoda environment."""
    try:
        # Get the status of the Cyoda environment using the entity service
        status = await entity_service.get_item(
            cyoda_token, 'cyoda_env', ENTITY_VERSION, id
        )
        return jsonify({"status": status}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_cyoda_env.route('/deploy/cyoda-env/statistics/<int:id>', methods=['GET'])
async def get_cyoda_env_statistics(id):
    """API endpoint to get the deployment statistics of Cyoda environment."""
    try:
        # Get the statistics of the Cyoda environment using the entity service
        statistics = await entity_service.get_item(
            cyoda_token, 'cyoda_env', ENTITY_VERSION, id
        )
        return jsonify({"statistics": statistics}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ```