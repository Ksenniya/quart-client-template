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
        )
    
    print("Final persisted entity ID:", entity_id)

if __name__ == "__main__":
    asyncio.run(main())