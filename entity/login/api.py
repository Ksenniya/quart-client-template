from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
import uuid
import asyncio

api_bp_login = Blueprint('api/login', __name__)

ENTITY_MODEL = 'login'

@api_bp_login.route('/auth/login', methods=['POST'])
async def add_login():
    """Create a new login."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        login_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({'login_id': login_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_login.route('/login/<id>', methods=['GET'])
async def get_id(id):
    """Retrieve a login by ID."""
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

@api_bp_login.route('/logins', methods=['GET'])
async def get_logins():
    """Retrieve all logins entries."""
    try:
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
