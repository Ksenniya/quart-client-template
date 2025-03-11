import asyncio
import logging
import datetime
import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request
from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

logger = logging.getLogger(__name__)

async def process_fetch_external(entity: dict):
    # Fetch external data using httpx
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get("https://jsonplaceholder.typicode.com/posts/1")
        response.raise_for_status()
        external_data = response.json()
    # Update the entity with fetched data
    entity["title"] = external_data.get("title", "")
    entity["body"] = external_data.get("body", "")
    # (Optional) Store external_data if needed for further processing
    entity["external_data"] = external_data

async def process_combine_result(entity: dict):
    # Combine title and body to produce a processed result
    title = entity.get("title", "").strip()
    body = entity.get("body", "").strip()
    processed_result = f"Processed: {title} & {body}"
    entity["processedResult"] = processed_result