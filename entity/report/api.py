# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION

api_bp_report = Blueprint('api/report', __name__)

@api_bp_report.route('/report/<report_id>', methods=['GET'])
async def get_report(report_id):
    """API endpoint to fetch the report details by report ID."""
    try:
        # Get the report entity using the entity service
        report = await entity_service.get_item(
            cyoda_token, 'report', ENTITY_VERSION, report_id
        )
        return jsonify({"report": report}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ```