import asyncio
import uuid
import base64
from datetime import datetime
from dataclasses import dataclass

from quart import Quart, request, jsonify, Response
import aiohttp
from quart_schema import QuartSchema, validate_request, validate_querystring

# Import external entity service functions and required constants
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

async def process_external_api(entity):
    data = {"email": entity.get("email")}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("http://example.com/external", json=data) as resp:
                if resp.status == 200:
                    response_json = await resp.json()
                    entity["supplementary"] = response_json
                    return entity
    except Exception as e:
        # In production, consider logging the exception
        pass
    entity["supplementary"] = {"result": "default"}
    return entity

async def process_set_createdAt(entity):
    if "createdAt" not in entity:
        entity["createdAt"] = datetime.utcnow().isoformat()
    return entity