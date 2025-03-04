import asyncio
import logging
import datetime
import httpx

logger = logging.getLogger(__name__)

# Business logic: Call external API and update the entity with the external data.
async def process_fetch_external_data(entity: dict):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("https://petstore.swagger.io/v2/pet", json=entity)
            response.raise_for_status()
            external_info = response.json()
    except Exception as e:
        logger.exception(e)
        external_info = {"info": "external service unavailable"}
    entity["externalData"] = external_info
    return entity

# Business logic: Mark the pet as processed by setting the processed timestamp.
async def process_set_processed_timestamp(entity: dict):
    entity["processedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    return entity