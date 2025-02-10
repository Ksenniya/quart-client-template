# Here is the `api.py` file implementing the endpoints for deploying a user application, as per the provided template:
# 
# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION

api_bp_user_app = Blueprint('api/user_app', __name__)

@api_bp_user_app.route('/deploy/user_app', methods=['POST'])
async def add_user_app():
    """API endpoint to deploy a user application."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Add the user_app entity using the entity service
        user_app_id = await entity_service.add_item(
            cyoda_token, "user_app", ENTITY_VERSION, data
        )
        return jsonify({"user_app_id": user_app_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_user_app.route('/deploy/cancel/user_app/<int:id>', methods=['POST'])
async def cancel_user_app(id):
    """API endpoint to cancel a queued build of a user application."""
    # Since entity_service only has add_item and get_item,
    # We will return a message indicating the action was attempted.
    try:
        return jsonify({"message": f"Cancellation of user app with id {id} is attempted."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_user_app.route('/deploy/user_app/status/<int:id>', methods=['GET'])
async def get_user_app_status(id):
    """API endpoint to retrieve the deployment status of a user application."""
    try:
        # Normally you'd fetch the status from an external service, but entity_service does not support this.
        # Here we just return a mock response for the sake of demonstration.
        return jsonify({"user_app_id": id, "status": "In Progress"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_user_app.route('/deploy/user_app/statistics/<int:id>', methods=['GET'])
async def get_user_app_statistics(id):
    """API endpoint to retrieve deployment statistics of a user application."""
    try:
        # Again, we're simulating as entity_service does not support getting statistics.
        return jsonify({"user_app_id": id, "statistics": {"deployments": 15, "success": 12, "failed": 3}}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ```
# 
# ### Explanation
# - Each route corresponds to one of the defined endpoints, using the `add_item` method where appropriate.
# - The `/deploy/cancel/user_app/<int:id>` endpoint, which logically would interact with an entity, has been stubbed as the entity service does not support cancellation functionality.
# - Similarly, the `/deploy/user_app/status/<int:id>` and `/deploy/user_app/statistics/<int:id>` endpoints return mock data since the `entity_service` does not provide means of fetching status or statistics.