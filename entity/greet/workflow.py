Here is the implementation of the processors for the newly generated workflow, including the `process_notify_greet` function template. The processor is designed to handle notifications for the greet entity:

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
1. **`process_initiate_greet`**: This function initializes the greet process by updating the entity with a status indicating that the greet process has been initiated.
2. **`process_notify_greet`**: This function constructs a greeting message and simulates sending a notification. It updates the entity with the notification status and the final message sent to the user.

You can replace the print statement with actual notification logic as required. If you need additional processes or modifications, please let me know!