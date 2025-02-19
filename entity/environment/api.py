from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
import uuid
import asyncio

api_bp_environment = Blueprint('api/environment', __name__)

ENTITY_MODEL = 'environment'

@api_bp_environment.route('/deploy/environments', methods=['POST'])
async def add_environment():
    """Create a new environment."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        environment_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({'environment_id': environment_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_environment.route('/environment/<id>', methods=['GET'])
async def get_id(id):
    """Retrieve a environment by ID."""
    try:
        data = await entity_service.get_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            technical_id=id
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_environment.route('/environments', methods=['GET'])
async def get_environments():
    """Retrieve all environments entries."""
    try:
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
