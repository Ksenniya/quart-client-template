from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
import uuid
import asyncio

api_bp_auth = Blueprint('api/auth', __name__)

ENTITY_MODEL = 'auth'

@api_bp_auth.route('/auth', methods=['POST'])
async def add_auth():
    """Create a new auth."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        auth_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({'auth_id': auth_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_auth.route('/auth/<id>', methods=['GET'])
async def get_id(id):
    """Retrieve a auth by ID."""
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

@api_bp_auth.route('/auths', methods=['GET'])
async def get_auths():
    """Retrieve all auths entries."""
    try:
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
