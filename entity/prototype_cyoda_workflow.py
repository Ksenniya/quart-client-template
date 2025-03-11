#!/usr/bin/env python3
import asyncio
import random

ENTITY_VERSION = "1.0"  # always use this constant

# Simulated entity service with methods for persisting primary and secondary entities
class EntityService:
    async def add_item(self, token, entity_model, entity_version, entity, workflow):
        # Apply the workflow function asynchronously to the entity before persistence.
        processed_entity = await workflow(entity)
        # Persist the processed entity (primary entity)
        print(f"Persisting {entity_model} with version {entity_version}: {processed_entity}")
        # Return a simulated entity ID
        return random.randint(1000, 9999)

    async def add_secondary_item(self, token, entity_model, entity_version, entity):
        # Persist a secondary/supplementary entity (different from the current entity_model)
        print(f"Persisting secondary {entity_model} with version {entity_version}: {entity}")
        return random.randint(1000, 9999)

# Async utility function to send a notification
async def send_async_notification(message):
    await asyncio.sleep(0.5)  # simulate network delay
    print(f"Notification sent: {message}")

# Async utility function to log an operation
async def log_async_operation(detail):
    await asyncio.sleep(0.2)  # simulate IO delay
    print(f"Log entry: {detail}")

# Workflow function for the 'item' entity.
# This function is invoked just before the primary entity is persisted.
async def process_item(entity):
    # Modify entity state
    entity["status"] = "processed"
    
    # Offload async tasks (e.g., notification, logging) from the endpoint to the workflow.
    await asyncio.gather(
        send_async_notification("Entity processed successfully."),
        log_async_operation("Processing 'item' entity in workflow."),
    )
    
    # Example: Persist supplementary data for a different entity_model.
    # Note: We create a new instance of EntityService or reuse an existing instance if available.
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
    # Update the primary entity state with details from the supplementary entity.
    entity["secondary_ref"] = secondary_id

    return entity

# Main function simulating the endpoint logic (controller).
async def main():
    cyoda_token = "sample_token"
    # Validated data object for primary entity
    data = {"id": 123, "name": "Sample Item", "value": 42}
    entity_service = EntityService()
    
    # Call add_item with the workflow function process_item; all async tasks are executed inside process_item.
    entity_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="item",
        entity_version=ENTITY_VERSION,
        entity=data,
        workflow=process_item  # Workflow function applied to the entity asynchronously before persistence.
    )
    
    print("Final persisted entity ID:", entity_id)

if __name__ == "__main__":
    asyncio.run(main())