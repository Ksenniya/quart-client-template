# Here’s the implementation of the `api.py` file for saving the `request_new_deployment` entity using Quart and the specified blueprint. We will utilize the constants `ENTITY_VERSION` and `cyoda_token` as instructed.
# 
# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION, cyoda_token
import logging

logger = logging.getLogger(__name__)

api_bp_request_new_deployment = Blueprint('api/request_new_deployment', __name__)

@api_bp_request_new_deployment.route('/request_new_deployment', methods=['POST'])
async def create_request_new_deployment():
    """
    Endpoint to create a new deployment request.
    """
    try:
        # Get the JSON data from the request
        data = await request.get_json()

        if not data or 'request_new_deployment' not in data:
            return jsonify({"error": "Invalid request data."}), 400

        # Prepare the deployment data
        deployment_data = data['request_new_deployment']

        # Call the entity service to add the new deployment
        result = await entity_service.add_item(cyoda_token, "request_new_deployment", ENTITY_VERSION, deployment_data)

        logger.info(f"New deployment request created successfully: {result}")

        return jsonify({"message": "Deployment request created successfully.", "deployment_id": result}), 201

    except Exception as e:
        logger.error(f"Error creating deployment request: {e}")
        return jsonify({"error": str(e)}), 500

# Register the blueprint in your main Quart application
# app.register_blueprint(api_bp_request_new_deployment, url_prefix='/api')
# ```
# 
# ### Explanation:
# - **Blueprint Definition**: 
#   - We define a new blueprint `api_bp_request_new_deployment` for handling requests related to the new deployment entity.
#   
# - **Endpoint**:
#   - The `/request_new_deployment` endpoint listens for `POST` requests.
#   - It expects a JSON payload with the `request_new_deployment` key.
#   
# - **Processing**:
#   - The function retrieves the JSON data from the request and validates it.
#   - It calls the `add_item` method from the `entity_service` to save the deployment request, using `cyoda_token` for authentication and `ENTITY_VERSION` for the versioning.
#   
# - **Logging and Response**:
#   - It logs success and returns a 201 status code with a success message and the deployment ID.
#   - If there is an error, it logs the error and returns a 500 status code with an error message.
# 
# You can register this blueprint in your main Quart application using the commented line at the end. If you have any specific suggestions or modifications, let me know!