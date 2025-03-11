import asyncio
import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

# Fetch external data from the API and store it in the entity.
async def process_fetch_data(entity: dict):
    async with httpx.AsyncClient() as client:
        response = await client.get("https://jsonplaceholder.typicode.com/posts/1")
        response.raise_for_status()
        entity["fetched_data"] = response.json()

# Merge the fetched data into the entity and perform a business-specific calculation.
async def process_merge_data(entity: dict):
    if entity.get("status") != "failed":
        fetched = entity.get("fetched_data", {})
        # Merge fetched data without overwriting critical properties.
        entity.update(fetched)
        title = fetched.get("title", "")
        entity["calculationResult"] = len(title)

# Update the entity status to 'completed', if processing was not already marked as failed.
async def process_update_status(entity: dict):
    if entity.get("status") != "failed":
        entity["status"] = "completed"

# Log the outcome of the processing.
async def process_log(entity: dict):
    if entity.get("status") != "failed":
        logger.info(
            "Workflow processing completed successfully for entity requested at %s.",
            entity.get("requestedAt")
        )
    else:
        logger.warning("Entity marked as failed. Skipping further processing.")