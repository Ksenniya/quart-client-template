# Here’s the implementation for the `api.py` file to save the entity `cancellation_request` using Quart, following your specifications.
# 
# ### `api.py`
# 
# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION, cyoda_token
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the Blueprint for the API
api_bp_cancellation_request = Blueprint('api/cancellation_request', __name__)

@api_bp_cancellation_request.route('/deploy/cancel/user_app/<id>', methods=['POST'])
async def save_cancellation_request(id):
    """Endpoint to save the cancellation request entity."""
    try:
        data = await request.json
        
        # Prepare current_entity for saving
        current_entity = {
            "user_name": data["user_name"],
            "request_id": data.get("request_id", id),  # Use provided ID or the one from data
            "application_id": data["application_id"],
            "status": "Requested",  # Initial status
            "comment": data.get("comment", ""),
            "readdIntoQueue": data.get("readdIntoQueue", False)
        }

        # Save the cancellation request entity
        response = await entity_service.add_item(cyoda_token, "cancellation_request", ENTITY_VERSION, current_entity)

        return jsonify({"message": "Cancellation request saved successfully", "id": response}), 201
    except Exception as e:
        logger.error(f"Error saving cancellation request: {e}")
        return jsonify({"error": "Failed to save cancellation request"}), 500
# ```
# 
# ### Explanation of the Code
# 
# - **Blueprint**: A Quart `Blueprint` named `api_bp_cancellation_request` is created for organizing the API routes related to cancellation requests.
#   
# - **Route Definition**: The route `/deploy/cancel/user_app/<id>` is defined for handling `POST` requests to save a cancellation request. The `<id>` parameter allows the ID to be specified in the URL.
# 
# - **Function Logic**:
#   - The function reads the JSON body from the request.
#   - It prepares the `current_entity` with essential details, including a status of "Requested."
#   - The `entity_service.add_item` method is called to save the cancellation request, utilizing the constants `cyoda_token` and `ENTITY_VERSION`.
#   - It returns a success message with the ID of the saved entity or an error message if something goes wrong.
# 
# This implementation allows users to manage cancellation requests effectively through the API. If you have any further adjustments or questions, feel free to let me know!