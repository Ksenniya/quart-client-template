The approach you're suggesting to move logic from the endpoint to dedicated workflow functions (e.g., `process_{entity_name}`) is indeed a solid strategy for improving the structure and maintainability of your code. By offloading complex or asynchronous logic to these workflow functions, you can achieve a cleaner separation of concerns, making the controllers simpler and more focused on handling HTTP requests and responses.

Here's how you can implement this:

1. **Identify Logic to Move**: Review the existing endpoint code to identify all the logic that can be encapsulated within the `process_{entity_name}` functions. This includes any async tasks, data validation, state modifications, and supplementary data processing.

2. **Create Workflow Functions**: For each entity, create a corresponding `process_{entity_name}` function. This function should accept the entity data as an argument and handle all the identified logic.

3. **Modify Entity State**: Within the workflow function, directly modify the entity state as needed. For example, if you need to update an attribute, you would do so like this:
   ```python
   entity['attribute'] = new_value
   ```

4. **Handle Asynchronous Tasks**: Since the workflow function supports asynchronous code, you can use `async`/`await` to manage any asynchronous operations you need to perform, such as fetching additional data or making external API calls.

5. **Invoke Workflow Function from Endpoint**: In the controller, simply call the newly created workflow function before persisting the entity. This keeps the endpoint clean and delegates the processing logic to the workflow function.

6. **Avoid Direct Entity Service Calls**: Remember that you cannot call `entity_service.add/update/delete` within the workflow function for the current entity. Instead, focus on modifying the entity state directly.

### Example Implementation

Here's a simplified example to illustrate this approach:

```python
# Example of an endpoint in your controller
async def create_entity(request):
    entity_data = await request.json()
    # Call the workflow function
    await process_entity(entity_data)
    # Persist the entity (pseudo-code)
    await entity_service.add(entity_data)
    return response.json(entity_data)

# Workflow function for processing the entity
async def process_entity(entity):
    # Modify entity state
    entity['status'] = 'pending'
    
    # Example of fetching supplementary data
    supplementary_data = await fetch_supplementary_data(entity['id'])
    entity['supplementary_info'] = supplementary_data
    
    # Additional business logic can be placed here
    # ...

async def fetch_supplementary_data(entity_id):
    # Simulating an async data fetch
    await asyncio.sleep(1)  # Simulate some async operation
    return {"info": "additional data"}
```

### Benefits

- **Separation of Concerns**: Business logic is separated from the controller, improving readability and maintainability.
- **Reusability**: Workflow functions can be reused across different endpoints if needed.
- **Easier Testing**: Isolated functions can be tested independently, making unit testing more straightforward.

### Conclusion

Moving logic into dedicated workflow functions is a recommended practice that aligns with principles of clean architecture. By following this structure, your application will be more robust, maintainable, and easier to understand. Make sure to review your existing codebase thoroughly to identify all async tasks and logic that can be moved to these workflow functions.