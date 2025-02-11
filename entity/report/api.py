# Here is the `api.py` file implementing the entity report endpoints based on the provided template. The endpoints are designed to handle the creation and retrieval of report entities.
# 
# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION

api_bp_report = Blueprint('api/report', __name__)

@api_bp_report.route('/report-request', methods=['POST'])
async def add_report():
    """API endpoint to initiate the report creation process and send the report via email."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Add the report entity using the entity service
        report_id = await entity_service.add_item(
            cyoda_token, "report", ENTITY_VERSION, data
        )
        return jsonify({"reportId": report_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_report.route('/report/<report_id>', methods=['GET'])
async def get_report(report_id):
    """API endpoint to retrieve the stored report by its ID."""
    try:
        # Get the report entity using the entity service
        report_data = await entity_service.get_item(
            cyoda_token, "report", ENTITY_VERSION, report_id
        )
        return jsonify(report_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ```
# 
# ### Explanation:
# 
# - **Blueprint**: The `api_bp_report` blueprint is created for the report entity.
#   
# - **POST /report-request**: This endpoint initiates the report creation process. It expects a JSON payload and uses the `add_item` method from the `entity_service` to store the report. If successful, it returns the `reportId`.
# 
# - **GET /report/<report_id>**: This endpoint retrieves a stored report by its ID using the `get_item` method from the `entity_service`. It returns the report data if found.
# 
# This implementation adheres strictly to the provided template and requirements. If you have any further questions or need additional modifications, feel free to ask!