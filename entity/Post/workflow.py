async def process_create_post(entity: dict):
    # Simulate the creation of a post
    entity["status"] = "created"
    entity["workflowProcessed"] = True
    return entity

async def process_update_post(entity: dict):
    # Simulate the update of a post
    entity["status"] = "updated"
    entity["workflowProcessed"] = True
    return entity

async def process_delete_post(entity: dict):
    # Simulate the deletion of a post
    entity["status"] = "deleted"
    entity["workflowProcessed"] = True
    return entity

async def process_retrieve_post(entity: dict):
    # Simulate retrieving a post
    entity["status"] = "retrieved"
    entity["workflowProcessed"] = True
    return entity

async def process_like_post(entity: dict):
    # Simulate liking a post
    if "likes" not in entity:
        entity["likes"] = 0
    entity["likes"] += 1
    entity["workflowProcessed"] = True
    return entity