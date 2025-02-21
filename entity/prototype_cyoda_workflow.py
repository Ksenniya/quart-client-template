Yes, that's exactly the right approach. By moving logic from the endpoint into a dedicated workflow function (for example, process_companies for the "companies" model), you achieve several benefits:

• Clear Separation of Concerns – The controller (endpoint) remains lightweight and handles only request/response tasks. All complex business logic and asynchronous operations move into the workflow function.
  
• Robustness and Maintainability – Centralizing asynchronous processing (such as calling external APIs, enriching data with LEI information, etc.) in the workflow function makes it easier to maintain, test, and extend without impacting the endpoint code.

• Consistent Entity State Updates – The workflow is applied on the entity right before persistence. This ensures that any transformation or additional enrichment (or secondary data creation) is applied directly to the entity data without having to call add/update on the same entity model, which prevents issues like infinite recursion.

• Asynchronous Processing Capabilities – Since the workflow function supports asynchronous code, you can handle any task—fire-and-forget tasks, external API calls, etc.—in a structured manner. This makes it a direct alternative to using ad-hoc async processing from within the controller.

Keep in mind:
– You can modify the entity directly (for example: entity['attribute'] = new_value) during workflow execution so that the new state will be persisted.
– You are allowed to call entity_service.add_item/update/delete on different entity_models in the workflow if supplementary data needs to be persisted.
– You must not perform add/update/delete on the current (same) entity_model inside its workflow to avoid recursion.

This design leads to a cleaner, more robust architecture with controllers free from excessive logic and workflow functions handling all business rules and asynchronous processing before final persistence.