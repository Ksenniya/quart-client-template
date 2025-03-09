def process_start(entity):
    print("Starting the process for post:", entity)

def process_create_post(entity):
    print("Creating post with content:", entity)

def process_review_post(entity):
    print("Reviewing post for approval:", entity)

def process_check_approval(entity):
    # Placeholder for approval check logic
    # Assuming a simple condition for demonstration
    is_approved = True  # This would be determined by actual review logic
    if is_approved:
        return process_publish_post(entity)
    else:
        return process_edit_post(entity)

def process_publish_post(entity):
    print("Publishing post:", entity)
    return process_archive_post(entity)

def process_edit_post(entity):
    print("Editing post:", entity)
    return process_review_post(entity)  # Loop back to review after editing

def process_archive_post(entity):
    print("Archiving post for records:", entity)
    return process_end(entity)

def process_end(entity):
    print("Process completed for post:", entity)

# Example usage
post_data = {
    "userId": 1,
    "id": 1,
    "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
    "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"
}

# Starting the workflow
process_start(post_data)