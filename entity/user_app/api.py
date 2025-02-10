# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION

api_bp_user_app = Blueprint('api/user_app', __name__)

@api_bp_user_app.route('/deploy/user_app', methods=['POST'])
async def add_user_app():
    """API endpoint to deploy user application."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Deploy the user application using the entity service
        user_app_id = await entity_service.add_item(
            cyoda_token, 'user_app', ENTITY_VERSION, data
        )
        return jsonify({"user_app_id": user_app_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_user_app.route('/deploy/cancel/user_app/<int:id>', methods=['POST'])
async def cancel_user_app(id):
    """API endpoint to cancel the user app deployment."""
    try:
        # Cancel the user application deployment using the entity service
        await entity_service.cancel_item(
            cyoda_token, 'user_app', ENTITY_VERSION, id
        )
        return jsonify({"message": "User app deployment cancelled successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_user_app.route('/deploy/user_app/status/<int:id>', methods=['GET'])
async def get_user_app_status(id):
    """API endpoint to get the deployment status of user app."""
    try:
        # Get the status of the user application deployment using the entity service
        status = await entity_service.get_item_status(
            cyoda_token, 'user_app', ENTITY_VERSION, id
        )
        return jsonify({"status": status}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_user_app.route('/deploy/user_app/statistics/<int:id>', methods=['GET'])
async def get_user_app_statistics(id):
    """API endpoint to get the deployment statistics of user app."""
    try:
        # Get the statistics of the user application deployment using the entity service
        statistics = await entity_service.get_item_statistics(
            cyoda_token, 'user_app', ENTITY_VERSION, id
        )
        return jsonify({"statistics": statistics}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ```