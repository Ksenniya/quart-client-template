import json

workflow_data = {
    "name": "Post Management Workflow",
    "description": "A workflow for creating, reviewing, and publishing posts.",
    "transitions": [
        {
            "name": "create_post",
            "description": "Add post content",
            "start_state": "None",
            "start_state_description": "Initial state",
            "end_state": "Post_created",
            "end_state_description": "A post has been created",
            "automated": True,
            "processes": {
                "schedule_transition_processors": [],
                "externalized_processors": [
                    {
                        "name": "process_create_post",
                        "description": "Creates a new post from the provided entity data."
                    }
                ]
            }
        },
        {
            "name": "review_post",
            "description": "Review for approval",
            "start_state": "Post_created",
            "start_state_description": "A post has been created",
            "end_state": "Post_reviewed",
            "end_state_description": "Post has been reviewed",
            "automated": True,
            "processes": {
                "schedule_transition_processors": [],
                "externalized_processors": [
                    {
                        "name": "process_review_post",
                        "description": "Reviews the created post for approval."
                    }
                ]
            }
        },
        {
            "name": "approve_post",
            "description": "Approve post for publication",
            "start_state": "Post_reviewed",
            "start_state_description": "Post has been reviewed",
            "end_state": "Post_published",
            "end_state_description": "Post has been published",
            "automated": True,
            "processes": {
                "schedule_transition_processors": [],
                "externalized_processors": [
                    {
                        "name": "process_approve_post",
                        "description": "Approves the post for publication."
                    }
                ]
            }
        },
        {
            "name": "edit_post",
            "description": "Make necessary changes to the post",
            "start_state": "Post_reviewed",
            "start_state_description": "Post has been reviewed",
            "end_state": "Post_created",
            "end_state_description": "Post has been created after edits",
            "automated": True,
            "processes": {
                "schedule_transition_processors": [],
                "externalized_processors": [
                    {
                        "name": "process_edit_post",
                        "description": "Edits the post based on feedback."
                    }
                ]
            }
        },
        {
            "name": "archive_post",
            "description": "Save post for records",
            "start_state": "Post_published",
            "start_state_description": "Post has been published",
            "end_state": "Workflow_completed",
            "end_state_description": "Process completed and post archived",
            "automated": True,
            "processes": {
                "schedule_transition_processors": [],
                "externalized_processors": [
                    {
                        "name": "process_archive_post",
                        "description": "Archives the published post."
                    }
                ]
            }
        }
    ]
}

# Convert the workflow data to JSON
json_workflow = json.dumps(workflow_data)

# Example output
print(json_workflow)