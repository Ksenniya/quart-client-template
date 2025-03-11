#!/usr/bin/env python3
import asyncio

ENTITY_VERSION = "1.0"  # always use this constant

# Simulated entity service with add_item function that applies a workflow function
class EntityService:
    async def add_item(self, token, entity_model, entity_version, entity, workflow):
        # Apply the workflow function asynchronously to the entity before persistence
        processed_entity = await workflow(entity)
        # Simulate persisting the processed entity (e.g., saving to a database)
        print(f"Persisting {entity_model} with version {entity_version}: {processed_entity}")
        # Return a simulated entity_id
        return 1  # replace with actual persistence logic as needed

# Workflow function for the 'item' entity
async def process_item(entity):
    # Modify the entity state as required before persistence
    entity["status"] = "processed"
    # Example: perform additional asynchronous actions here if needed
    return entity

async def main():
    cyoda_token = "sample_token"
    data = {"name": "Sample Item", "value": 42}  # the validated data object
    entity_service = EntityService()
    
    # Call add_item with process_item as the workflow function
    entity_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="item",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=data,  # the validated data object
        workflow=process_item  # Workflow function applied to the entity asynchronously before persistence
    )
    print("Entity ID:", entity_id)

if __name__ == "__main__":
    asyncio.run(main())