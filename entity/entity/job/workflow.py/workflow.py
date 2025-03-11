import asyncio
import logging
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

# External API URLs for JSON Placeholder
JSON_PLACEHOLDER_URL_1 = "https://jsonplaceholder.typicode.com/posts/1"
JSON_PLACEHOLDER_URL_2 = "https://jsonplaceholder.typicode.com/posts/2"

async def process_fetch_placeholder_data_1(entity: dict):
    # Calls the JSON Placeholder API and stores the result in the entity.
    async with httpx.AsyncClient() as client:
        response = await client.get(JSON_PLACEHOLDER_URL_1)
        response.raise_for_status()
        placeholder_data = response.json()
    entity["placeholder_data_1"] = placeholder_data
    logger.info("JSON Placeholder data 1 retrieved successfully in process_fetch_placeholder_data_1")

async def process_fetch_placeholder_data_2(entity: dict):
    # Calls the JSON Placeholder API and stores the result in the entity.
    async with httpx.AsyncClient() as client:
        response = await client.get(JSON_PLACEHOLDER_URL_2)
        response.raise_for_status()
        placeholder_data = response.json()
    entity["placeholder_data_2"] = placeholder_data
    logger.info("JSON Placeholder data 2 retrieved successfully in process_fetch_placeholder_data_2")

async def process_handle_payload(entity: dict):
    # Processes the external data based on the payload stored in the entity.
    payload = entity.get("payload", {})
    external_data = entity.get("external_data", {})
    placeholder_data_1 = entity.get("placeholder_data_1", {})
    placeholder_data_2 = entity.get("placeholder_data_2", {})
    data_type = payload.get("data_type")
    
    # Business processing logic: for demonstration, return external_data or placeholder_data.
    processed_data = external_data if data_type == "external_api" else placeholder_data_1 if data_type == "placeholder_1" else placeholder_data_2
    entity["data"] = processed_data

async def process_set_completed(entity: dict):
    # Sets the entity state to completed along with processed timestamp.
    entity["status"] = "completed"
    entity["processedAt"] = datetime.utcnow().isoformat()