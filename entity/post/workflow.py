import asyncio
import httpx
import logging
import datetime

logger = logging.getLogger(__name__)

# Processor to fetch post data from JSONPlaceholder API
async def process_fetch_post(entity: dict):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://jsonplaceholder.typicode.com/posts/1")
            response.raise_for_status()
            post_data = response.json()
            
            # Update the entity with fetched post data
            entity["userId"] = post_data.get("userId")
            entity["id"] = post_data.get("id")
            entity["title"] = post_data.get("title")
            entity["body"] = post_data.get("body")
            entity["workflowProcessedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
            
            return entity
    except Exception as e:
        logger.exception("Error fetching post data: %s", e)
        return entity  # Return the entity unchanged or apply error handling.

# Processor to persist the post entity to the database
async def process_persist_post(entity: dict):
    try:
        # Here you would have the logic to persist the entity to your database
        # For example:
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="post",
            entity_version=ENTITY_VERSION,
            entity=entity,
        )
        entity["workflowProcessed"] = True  # Mark as processed
        return entity
    except Exception as e:
        logger.exception("Error persisting post data: %s", e)
        return entity  # Return the entity unchanged or apply error handling.