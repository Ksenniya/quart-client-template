import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Business logic function: simulate asynchronous delay.
async def process_sleep(entity: dict):
    await asyncio.sleep(1)

# Business logic function: set the workflow processed timestamp.
async def process_set_timestamp(entity: dict):
    entity["workflowProcessedAt"] = datetime.utcnow().isoformat()

# Business logic function: validate the pet name and set a default if missing.
async def process_validate_name(entity: dict):
    if not entity.get("name"):
        entity["name"] = "Unnamed Pet"