# Here's the `api.py` file implementing the entity job endpoints as specified in your request. I've filled in the template accordingly:
# 
# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION

api_bp_job = Blueprint('api/job', __name__)

@api_bp_job.route('/job', methods=['POST'])
async def add_job():
    """API endpoint to create a new report."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Add the job entity using the entity service
        job_id = await entity_service.add_item(
            cyoda_token, 'job', ENTITY_VERSION, data
        )
        return jsonify({"job_id": job_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_job.route('/report/<report_id>', methods=['GET'])
async def get_report(report_id):
    """API endpoint to retrieve a report by its ID."""
    try:
        # Retrieve the report entity using the entity service
        report_data = await entity_service.get_item(
            cyoda_token, 'report', ENTITY_VERSION, report_id
        )
        return jsonify({"report_data": report_data}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ```
# 
# ### Explanation:
# 1. **Blueprint Creation**: The blueprint is created for the job entity with the name `api/job`.
# 2. **POST Endpoint**: The `/job` endpoint is defined to create a new report. It checks for JSON data and uses the `add_item` method from `entity_service` to add the job.
# 3. **GET Endpoint**: The `/report/<report_id>` endpoint retrieves a report by its ID using the `get_item` method from `entity_service`.
# 4. **Error Handling**: Both endpoints include error handling to return appropriate error messages and status codes.