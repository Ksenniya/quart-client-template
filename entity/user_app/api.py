from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
import uuid
import asyncio

api_bp_user_app = Blueprint('api/user_app', __name__)

ENTITY_MODEL = 'user_app'

@api_bp_user_app.route('/deploy/user-apps', methods=['POST'])
async def add_user_app():
    """Create a new user_app."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        user_app_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({'user_app_id': user_app_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_user_app.route('/deploy/user-apps/<id>/cancel', methods=['POST'])
async def add_user_app(id):
    """Create a new user_app."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        user_app_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({'user_app_id': user_app_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_user_app.route('/user_app/<id>', methods=['GET'])
async def get_id(id):
    """Retrieve a user_app by ID."""
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

@api_bp_user_app.route('/user_apps', methods=['GET'])
async def get_user_apps():
    """Retrieve all user_apps entries."""
    try:
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
