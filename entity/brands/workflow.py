import asyncio
import datetime
import aiohttp

from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from common.repository.cyoda.cyoda_init import init_cyoda
from common.config.config import ENTITY_VERSION
from app_init.app_init import cyoda_token, entity_service

async def process_validate_entity(entity):
    # Validate that the entity is a dict; if not, reset it to an empty dict.
    if not isinstance(entity, dict):
        entity.clear()
        entity.update({})

async def process_fetch_brands(entity):
    # Call external API to fetch brands and update entity accordingly.
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://api.practicesoftwaretesting.com/brands',
                headers={'accept': 'application/json'}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    entity["data"] = data
                    entity["status"] = "completed"
                else:
                    entity["status"] = f"error_{resp.status}"
    except Exception as e:
        entity["status"] = "failed"

async def process_update_timestamp(entity):
    # Update the entity with the current UTC timestamp.
    entity["requestedAt"] = datetime.datetime.utcnow().isoformat()