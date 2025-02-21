Yes, definitely. We can—and should—move most of the logic from our endpoints into the workflow functions. Doing so brings several benefits:

• Controllers become leaner and focus solely on request validation, authentication, and invoking a service method, while the business logic, state changes, and even asynchronous side tasks are encapsulated elsewhere.

• The workflow functions (e.g., process_cyoda_env_deployment or process_user_app_deployment) now serve as dedicated business logic components that run right before the entity is persisted. They can perform additional field updates, set timestamps, change status, or even launch asynchronous processing tasks without cluttering the endpoint.

• Since these workflow functions support asynchronous code, any “fire-and-forget” tasks (such as starting build processing) can be relocated there rather than being explicitly created in the controllers. This would make our code more robust, testable, and decoupled.

For example, instead of having the endpoint trigger an asynchronous task:
  asyncio.create_task(process_build(...))
we could incorporate the necessary asynchronous behavior directly inside the corresponding workflow function. That way, the entity_service.add_item call would not only persist the entity but also trigger the workflow logic that could update the entity state (queued, running, success, etc.) as part of the same centralized process.

In summary, moving the in-endpoint logic into workflow functions is the right approach. It frees the controllers from excessive logic, centralizes the business rules, and leverages asynchronous support in a natural way.