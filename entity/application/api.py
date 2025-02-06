# Here’s the implementation for the `api.py` file to save the entity application using Quart, following your specifications.
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
api_bp_application = Blueprint('api/application', __name__)

@api_bp_application.route('/deploy/user_app', methods=['POST'])
async def save_application():
    """Endpoint to save the application entity."""
    try:
        data = await request.json
        
        # Prepare current_entity for saving
        current_entity = {
            "user_name": data["user_name"],
            "name": data["name"],
            "repository_url": data["repository_url"],
            "status": "Pending",  # Initial status
            "deployment_parameters": data.get("deployment_parameters", {})
        }

        # Save the application entity
        response = await entity_service.add_item(cyoda_token, "application", ENTITY_VERSION, current_entity)

        return jsonify({"message": "Application saved successfully", "id": response}), 201
    except Exception as e:
        logger.error(f"Error saving application: {e}")
        return jsonify({"error": "Failed to save application"}), 500
# ```
# 
# ### Explanation of the Code
# 
# - **Blueprint**: A Quart `Blueprint` named `api_bp_application` is created for organizing the API routes related to application entities.
#   
# - **Route Definition**: The route `/deploy/user_app` is defined for handling `POST` requests to save an application.
# 
# - **Function Logic**:
#   - The function reads the JSON body from the request.
#   - It prepares the `current_entity` with necessary details, including a default status of "Pending".
#   - The `entity_service.add_item` method is called to save the application, utilizing the constants `cyoda_token` and `ENTITY_VERSION`.
#   - It returns a success message with the ID of the saved entity or an error message if something goes wrong.
# 
# This implementation facilitates the ability for users to manage their applications effectively through the API. If you have any further adjustments or questions, feel free to let me know!