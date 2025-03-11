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

async def process_set_processed(entity: dict):
    # Set the pet as processed
    entity["processed"] = True

async def process_set_timestamp(entity: dict):
    # Set the processed timestamp of the pet
    entity["processed_timestamp"] = time.time()

async def process_send_notification(entity: dict):
    try:
        # Simulate sending a notification for the pet entity
        await asyncio.sleep(0)  # Replace with actual async email/sms service call
        logger.info(f"Pet notification sent for pet id {entity.get('id')}")
    except Exception as e:
        logger.exception(f"Error in process_send_notification: {e}")