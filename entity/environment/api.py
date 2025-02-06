# Here’s the `api.py` file for the Quart application, implementing the endpoint to save the Environment entity. The file utilizes the `api_bp_environment` blueprint and includes the necessary imports, constants, and logic.
# 
# ```python
from quart import Blueprint, request, jsonify
import logging
from logic.app_init import entity_service
from connections import ingest_data as ingest_environment_data

# Constants
ENTITY_VERSION = "v1"  # Define your entity version here
CYODA_TOKEN = "your_token_here"  # Replace with your actual token logic

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Blueprint for environment API
api_bp_environment = Blueprint('api/environment', __name__)

@api_bp_environment.route('/save', methods=['POST'])
async def save_environment():
    """Endpoint to save an environment entity."""
    data = await request.json
    
    # Validate required fields
    if not data.get("environment_name") or not data.get("config"):
        return jsonify({"error": "Environment name and configuration are required"}), 400

    try:
        # Ingest environment data, if required
        raw_request_id = await ingest_environment_data(data)

        # Save environment entity to Cyoda
        environment = await entity_service.add("environment", data)

        # Return successful response with environment details and raw_request_id
        return jsonify({
            "environment_details": environment,
            "raw_request_id": raw_request_id,
            "token": CYODA_TOKEN  # Include the token in the response if needed
        }), 201

    except Exception as e:
        logger.error(f"Error saving environment: {e}")
        return jsonify({"error": str(e)}), 500
# ```
# 
# ### Explanation
# - **Blueprint Setup**: The blueprint `api_bp_environment` is created for the environment-related API.
# - **POST Endpoint**: The `/save` endpoint accepts a JSON payload to save an environment.
# - **Data Validation**: It checks for the required fields (environment_name and config) and returns an error if they are missing.
# - **Ingestion and Saving**: It uses the existing `ingest_data` function to handle necessary data ingestion, followed by saving the environment entity using `entity_service`.
# - **Response**: The endpoint returns environment details, the raw request ID, and a token upon successful creation or appropriate error messages in case of failure.
# 
# This implementation is ready for integration into your Quart application. If you need further modifications or additional features, feel free to ask!