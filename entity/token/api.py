from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
import uuid
import asyncio

api_bp_token = Blueprint('api/token', __name__)

ENTITY_MODEL = 'token'

@api_bp_token.route('/auth/token', methods=['POST'])
async def add_token():
    """Create a new token."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        token_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({'token_id': token_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_token.route('/token/<id>', methods=['GET'])
async def get_id(id):
    """Retrieve a token by ID."""
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

@api_bp_token.route('/tokens', methods=['GET'])
async def get_tokens():
    """Retrieve all tokens entries."""
    try:
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
