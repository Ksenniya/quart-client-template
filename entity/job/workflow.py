import asyncio
import logging
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

# External API URL for JSON Placeholder
JSON_PLACEHOLDER_URL = "https://jsonplaceholder.typicode.com/posts/1"

async def process_fetch_external_data(entity: dict):
    # Calls the external API and stores the result in the entity.
    async with httpx.AsyncClient() as client:
        response = await client.get(EXTERNAL_API_URL)
        response.raise_for_status()
        external_data = response.json()
    entity["external_data"] = external_data
    logger.info("External API data retrieved successfully in process_fetch_external_data")

async def process_fetch_placeholder_data(entity: dict):
    # Calls the JSON Placeholder API and stores the result in the entity.
    async with httpx.AsyncClient() as client:
        response = await client.get(JSON_PLACEHOLDER_URL)
        response.raise_for_status()
        placeholder_data = response.json()
    entity["placeholder_data"] = placeholder_data
    logger.info("JSON Placeholder data retrieved successfully in process_fetch_placeholder_data")

async def process_handle_payload(entity: dict):
    # Processes the external data based on the payload stored in the entity.
    payload = entity.get("payload", {})
    external_data = entity.get("external_data", {})
    placeholder_data = entity.get("placeholder_data", {})
    data_type = payload.get("data_type")
    
    # Business processing logic: for demonstration, return external_data or placeholder_data.
    processed_data = external_data if data_type == "external_api" else placeholder_data
    entity["data"] = processed_data

async def process_set_completed(entity: dict):
    # Sets the entity state to completed along with processed timestamp.
    entity["status"] = "completed"
    entity["processedAt"] = datetime.utcnow().isoformat()