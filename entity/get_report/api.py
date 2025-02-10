# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION

api_bp_report = Blueprint('api/report', __name__)


@api_bp_report.route('/api/generate-report', methods=['POST'])
async def generate_report():
    """This endpoint generates a report by downloading data, analyzing it, and storing the report."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Assume the data contains necessary parameters for report generation
    try:
        # Add a new report entity using the entity service
        report_id = await entity_service.add_item(
            cyoda_token, 'report', ENTITY_VERSION, data
        )
        return jsonify({"report_id": report_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp_report.route('/api/get-report', methods=['GET'])
async def get_report():
    """This endpoint retrieves the generated report from memory."""
    report_id = request.args.get('report_id')
    if not report_id:
        return jsonify({"error": "No report_id provided"}), 400

    try:
        # Fetch the report based on report_id using the entity service
        report_data = await entity_service.get_item(
            cyoda_token, 'report', ENTITY_VERSION, report_id
        )
        return jsonify(report_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ```