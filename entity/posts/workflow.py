def process_create_post(entity):
    """
    Process for creating a new post.
    :param entity: A dictionary containing the entity data.
    """
    post_data = entity.get("fields", {})
    # Validate the post data
    if not validate_post(post_data):
        raise ValueError("Invalid post data")
    # Save the post to the database
    save_post(post_data)

def process_edit_post(entity):
    """
    Process for editing an existing post.
    :param entity: A dictionary containing the entity data.
    """
    post_data = entity.get("fields", {})
    # Fetch the existing post
    existing_post = fetch_post(post_data.get("id"))
    if not existing_post:
        raise ValueError("Post not found")
    
    # Update the post with new data
    update_post(existing_post, post_data)

def process_delete_post(entity):
    """
    Process for deleting a post.
    :param entity: A dictionary containing the entity data.
    """
    post_id = entity.get("fields", {}).get("id")
    if not post_id:
        raise ValueError("Post ID is required for deletion")
    
    # Validate the delete operation
    if not validate_delete(post_id):
        raise ValueError("Cannot delete the post")
    
    # Remove the post from the database
    remove_post(post_id)

def validate_post(post_data):
    """
    Validate the post data.
    :param post_data: A dictionary containing the post fields.
    :return: Boolean indicating whether the post data is valid.
    """
    required_fields = ['userId', 'title', 'body']
    for field in required_fields:
        if field not in post_data:
            return False
    return True

def save_post(post_data):
    """
    Save the post to the database (dummy implementation).
    :param post_data: A dictionary containing the post fields.
    """
    # Implementation to save the post to the database
    print("Post saved:", post_data)

def fetch_post(post_id):
    """
    Fetch the existing post by its ID (dummy implementation).
    :param post_id: The ID of the post to fetch.
    :return: A dictionary representing the post if found, otherwise None.
    """
    # Dummy implementation which simulates fetching a post
    return {"id": post_id, "userId": 1, "title": "Sample Post", "body": "This is a sample post."}

def update_post(existing_post, post_data):
    """
    Update the existing post with new data (dummy implementation).
    :param existing_post: The existing post to update.
    :param post_data: A dictionary containing the new post fields.
    """
    # Implementation to update the post in the database
    existing_post.update(post_data)
    print("Post updated:", existing_post)

def validate_delete(post_id):
    """
    Validate the delete operation for a post (dummy implementation).
    :param post_id: The ID of the post to validate for deletion.
    :return: Boolean indicating whether the post can be deleted.
    """
    # Dummy implementation which allows all deletions
    return True

def remove_post(post_id):
    """
    Remove the post from the database (dummy implementation).
    :param post_id: The ID of the post to remove.
    """
    # Implementation to remove the post from the database
    print("Post with ID", post_id, "removed.")