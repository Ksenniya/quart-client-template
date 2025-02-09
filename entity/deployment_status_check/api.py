# Here’s the implementation of the `api.py` file for saving the `deployment_status_check` entity using Quart and the specified blueprint. We will utilize the constants `ENTITY_VERSION` and `cyoda_token` as instructed.
# 
# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION, cyoda_token
import logging

logger = logging.getLogger(__name__)

api_bp_deployment_status_check = Blueprint('api/deployment_status_check', __name__)

@api_bp_deployment_status_check.route('/deployment_status_check', methods=['POST'])
async def create_deployment_status_check():
    """
    Endpoint to create a new deployment status check request.
    """
    try:
        # Get the JSON data from the request
        data = await request.get_json()

        if not data or 'deployment_status_check' not in data:
            return jsonify({"error": "Invalid request data."}), 400

        # Prepare the deployment status check data
        status_check_data = data['deployment_status_check']

        # Call the entity service to add the new deployment status check
        result = await entity_service.add_item(cyoda_token, "deployment_status_check", ENTITY_VERSION, status_check_data)

        logger.info(f"New deployment status check request created successfully: {result}")

        return jsonify({"message": "Deployment status check request created successfully.", "status_check_id": result}), 201

    except Exception as e:
        logger.error(f"Error creating deployment status check request: {e}")
        return jsonify({"error": str(e)}), 500

# Register the blueprint in your main Quart application
# app.register_blueprint(api_bp_deployment_status_check, url_prefix='/api')
# ```
# 
# ### Explanation:
# - **Blueprint Definition**: 
#   - A new blueprint `api_bp_deployment_status_check` is defined for handling requests related to the deployment status check entity.
#   
# - **Endpoint**:
#   - The `/deployment_status_check` endpoint listens for `POST` requests.
#   - It expects a JSON payload with the `deployment_status_check` key.
#   
# - **Processing**:
#   - The function retrieves the JSON data from the request and validates it.
#   - It calls the `add_item` method from the `entity_service` to save the deployment status check, using `cyoda_token` for authentication and `ENTITY_VERSION` for versioning.
#   
# - **Logging and Response**:
#   - It logs success and returns a 201 status code with a success message and the status check ID.
#   - If there is an error, it logs the error and returns a 500 status code with an error message.
# 
# You can register this blueprint in your main Quart application using the commented line at the end. If you have any specific suggestions or modifications, feel free to let me know!