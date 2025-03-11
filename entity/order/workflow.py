import asyncio
import datetime
import logging

logger = logging.getLogger(__name__)

# Business logic: simulate a processing delay
async def process_simulate_delay(entity: dict):
    await asyncio.sleep(2)
    return entity

# Business logic: update order status directly in the entity data
async def process_update_status(entity: dict):
    entity["status"] = "processed"
    return entity

# Business logic: add a timestamp to the entity data
async def process_add_timestamp(entity: dict):
    entity["workflowProcessedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    return entity