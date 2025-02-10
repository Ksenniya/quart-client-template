# Here’s the implementation of the `api.py` file for the activity entity endpoints, following the specified template and requirements:
# 
# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION

api_bp_activity = Blueprint('api/Activities', __name__)

@api_bp_activity.route('/Activities', methods=['GET'])
async def get_activities():
    """API endpoint to fetch all activities from the external API."""
    try:
        # Since we are fetching from an external API, we use the entity service to get the items
        activities = await entity_service.get_item(
            cyoda_token, "activity", ENTITY_VERSION, "all"  # Assuming 'all' fetches all activities
        )
        return jsonify({"activities": activities}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_activity.route('/Activities/<int:entity_id>', methods=['GET'])
async def get_activity(entity_id):
    """API endpoint to fetch details for a specific activity from the external API."""
    try:
        # Fetch the specific activity using the entity service
        activity = await entity_service.get_item(
            cyoda_token, "activity", ENTITY_VERSION, entity_id
        )
        return jsonify({"activity": activity}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ```
# 
# ### Explanation:
# - **Imports**: The necessary modules are imported as specified in the template.
# - **Blueprint**: The `Blueprint` is created for the activity entity.
# - **GET Endpoint (`/Activities`)**: This endpoint is used to fetch all activities. It calls the `get_item` method of the `entity_service` to retrieve all activities, assuming that using "all" as an ID fetches all records. The results are returned in JSON format.
# - **GET Endpoint (`/Activities/{id}`)**: This endpoint fetches details for a specific activity by its ID. It uses the `get_item` method of the `entity_service` to retrieve the activity based on the provided `entity_id`. The activity details are returned in JSON format.
# 
# This implementation strictly follows the provided template and adheres to the specified functionalities for the activity entity. If you have any further requirements or adjustments, please let me know!