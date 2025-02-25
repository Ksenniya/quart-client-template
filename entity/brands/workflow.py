import asyncio
import datetime
import aiohttp
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request
from common.config.config import ENTITY_VERSION
from app_init.app_init import cyoda_token, entity_service
from common.repository.cyoda.cyoda_init import init_cyoda

# Workflow orchestration for processing multiple brand entities.
async def process_brands(entities: list):
    # Orchestrate processing of all entities concurrently.
    tasks = [process_brand(entity) for entity in entities]
    processed_entities = await asyncio.gather(*tasks)
    return processed_entities