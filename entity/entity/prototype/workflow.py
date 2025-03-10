import asyncio
import logging
import httpx

logger = logging.getLogger(__name__)

ENTITY_MODEL = "entity/prototype"

# Business logic: fetch data from the external API and update the entity.
async def process_fetch_data(entity: dict):
    external_api_url = "https://petstore.swagger.io/v2/swagger.json"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(external_api_url)
        response.raise_for_status()
        data = response.json()
    entity["data"] = data