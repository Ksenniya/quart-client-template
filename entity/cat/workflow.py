Here are the implementations for the processors for the newly generated workflow, including the `process_initiate_greet` and `process_notify_greet` functions. Each function follows the specified structure, taking one argument `entity`.

```python
async def process_initiate_greet(entity: dict):
    # Example code for initiating the greet process
    entity["greet_status"] = "initiated"
    entity["workflowProcessed"] = True


async def process_notify_greet(entity: dict):
    # Example code for notifying the user with the greeting
    user_name = entity.get("name", "Guest")
    greeting_message = f"Hello, {user_name}!"
    
    # Simulate sending a notification (e.g., via email, SMS, etc.)
    # Here we just log it for demonstration purposes
    print(f"Sending notification: {greeting_message}")
    
    entity["notification_status"] = "sent"
    entity["final_message"] = greeting_message
    entity["workflowProcessed"] = True
```

### Explanation:
1. **`process_initiate_greet`**: This function updates the entity to indicate that the greet process has been initiated. It sets the `greet_status` field and marks the workflow as processed.
   
2. **`process_notify_greet`**: This function constructs a greeting message based on the name provided in the entity. It simulates sending a notification (using a print statement) and updates the entity with the notification status and the final message sent to the user.

Each function is designed to ensure that the entity is updated appropriately for the workflow's requirements. If you need further modifications or additional processes, please let me know!