import asyncio
import httpx
import logging
import time
from dataclasses import dataclass

from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

logger = logging.getLogger(__name__)

async def process_hash_password(entity: dict):
    # Business logic: hash the user's password
    if "password" in entity:
        entity["password"] = "hashed_" + entity["password"]

async def process_send_welcome_email(entity: dict):
    try:
        # Business logic: send welcome email asynchronously
        await asyncio.sleep(0)  # Replace with actual async email service call
        logger.info(f"Welcome email sent to user id {entity.get('id')}")
    except Exception as e:
        logger.exception(f"Error in process_send_welcome_email: {e}")