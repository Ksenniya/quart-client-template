import asyncio
import random

ENTITY_VERSION = "1.0"  # always use this constant

# Dummy EntityService for supplementary data persistence.
class EntityService:
    async def add_secondary_item(self, token, entity_model, entity_version, entity):
        await asyncio.sleep(0.1)  # simulate network delay
        return f"secondary_{random.randint(100, 999)}"

async def send_async_notification(message):
    await asyncio.sleep(0.5)  # simulate network delay
    print(f"Notification sent: {message}")

async def log_async_operation(detail):
    await asyncio.sleep(0.2)  # simulate IO delay
    print(f"Log entry: {detail}")

# Business logic functions (should only modify the entity state)
async def process_status(entity: dict):
    entity["status"] = "processed"

async def process_notification(entity: dict):
    await send_async_notification("Entity processed successfully.")

async def process_logging(entity: dict):
    await log_async_operation("Processing 'item' entity in workflow.")

async def process_secondary(entity: dict):
    # Persist supplementary data for a different entity_model.
    entity_service = EntityService()
    secondary_data = {
        "ref_id": entity.get("id", "N/A"),
        "metadata": "extra information"
    }
    secondary_id = await entity_service.add_secondary_item(
        token="secondary_token",
        entity_model="secondary_item",
        entity_version=ENTITY_VERSION,
        entity=secondary_data
    )
    entity["secondary_ref"] = secondary_id