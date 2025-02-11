# Here’s the `api.py` file implementing the `report` entity endpoints based on the provided template. The endpoints include the `POST /report-request` for creating a report and the `GET /report/<entity_id>` for retrieving a report by its ID.
# 
# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION

api_bp_report = Blueprint('api/report', __name__)

@api_bp_report.route('/report-request', methods=['POST'])
async def add_report():
    """API endpoint to initiate the report creation process and send an email with the current Bitcoin conversion rates."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Add the report entity using the entity service
        report_id = await entity_service.add_item(
            cyoda_token, 'report', ENTITY_VERSION, data
        )
        return jsonify({"report_id": report_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_report.route('/report/<entity_id>', methods=['GET'])
async def get_report(entity_id):
    """API endpoint to retrieve a previously generated report by its ID."""
    try:
        # Get the report entity using the entity service
        report_data = await entity_service.get_item(
            cyoda_token, 'report', ENTITY_VERSION, entity_id
        )
        return jsonify(report_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ```
# 
# ### Explanation:
# - **Blueprint**: The `api_bp_report` blueprint is created for the `report` entity.
# - **POST Endpoint**: The `/report-request` endpoint receives data to create a report and uses the `add_item` method from `entity_service` to store it.
# - **GET Endpoint**: The `/report/<entity_id>` endpoint retrieves a report by its ID using the `get_item` method from `entity_service`.
# - **Error Handling**: Both endpoints include error handling to return appropriate error messages.
# 
# This implementation adheres to the specified template and requirements. If you need further modifications or additional features, feel free to ask!