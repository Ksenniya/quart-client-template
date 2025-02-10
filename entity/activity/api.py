# ```python
from quart import Blueprint, request, jsonify
import httpx
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION

api_bp_ACTIVITY = Blueprint('api/activity', __name__)

EXTERNAL_API_BASE_URL = "https://fakerestapi.azurewebsites.net/api/v1/Activities"


@api_bp_ACTIVITY.route('/activities', methods=['GET'])
async def fetch_activities():
    """API endpoint to fetch a list of activities from an external API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(EXTERNAL_API_BASE_URL)
            response.raise_for_status()  # Raise exception for HTTP errors
            activities = response.json()
            return jsonify(activities), response.status_code
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp_ACTIVITY.route('/activities/<int:activity_id>', methods=['GET'])
async def fetch_activity_details(activity_id):
    """API endpoint to fetch detailed activity data by activity ID from an external API."""
    try:
        url = f"{EXTERNAL_API_BASE_URL}/{activity_id}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()  # Raise exception for HTTP errors
            activity_details = response.json()
            return jsonify(activity_details), response.status_code
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ```