async def process_create_post(entity: dict):
    # Logic for creating a post
    # Example: final_result = await create_post_in_db(entity)
    final_result = "Post created"  # Placeholder for actual implementation
    entity["final_result"] = final_result
    entity["workflowProcessed"] = True

async def process_read_post(entity: dict):
    # Logic for reading a post
    # Example: post_data = await read_post_from_db(entity["id"])
    post_data = {"id": entity["id"], "title": "Sample Title", "body": "Sample Body"}  # Placeholder
    entity["post_data"] = post_data
    entity["workflowProcessed"] = True

async def process_update_post(entity: dict):
    # Logic for updating a post
    # Example: updated_result = await update_post_in_db(entity)
    updated_result = "Post updated"  # Placeholder for actual implementation
    entity["final_result"] = updated_result
    entity["workflowProcessed"] = True

async def process_delete_post(entity: dict):
    # Logic for deleting a post
    # Example: deletion_result = await delete_post_from_db(entity["id"])
    deletion_result = "Post deleted"  # Placeholder for actual implementation
    entity["final_result"] = deletion_result
    entity["workflowProcessed"] = True