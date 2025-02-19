from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
import uuid
import asyncio

api_bp_status = Blueprint('api/status', __name__)

ENTITY_MODEL = 'status'

@api_bp_status.route('/deploy/environments/<build_id>/status', methods=['GET'])
async def get_build_id(build_id):
    """Retrieve status information."""
    try:
        data = await entity_service.get_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            technical_id=build_id
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_status.route('/deploy/user-apps/<build_id>/status', methods=['GET'])
async def get_build_id(build_id):
    """Retrieve status information."""
    try:
        data = await entity_service.get_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            technical_id=build_id
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
