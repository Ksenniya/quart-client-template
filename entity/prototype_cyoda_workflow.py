Yes, we can—and probably should—move more of the processing logic out of the endpoint and into dedicated workflow functions. The endpoint’s job should be limited to validating the request, preparing the initial entity data, and then delegating everything else to background or workflow functions. That way, the controller stays lean and focused on handling HTTP-specific tasks while business logic (including async “fire‐and‐forget” tasks) is encapsulated in separate functions.

For example, in our current design the endpoint:
• Creates the job entity.
• Fires off the asynchronous processing task (process_entity).

We could refactor this so that the workflow function (like process_companies_job) is responsible for any preliminary processing or transformation of the entity data just before its persistence. Although the workflow function should remain lightweight and synchronous (doing only transformations on the job data), if your “fire and forget” logic is not tightly coupled to immediately persisting the entity you might consider moving any simple state updates (or even triggers for external async tasks) into this workflow function.

A couple of options to consider:

1. Move Pure Data Transformations into the Workflow Function:
 • For example, if there is any minor business logic (setting default values, timestamps, flags, etc.) that’s currently done in the endpoint, you can shift that directly into process_companies_job.
 • This function would be passed as the workflow argument to entity_service.add_item and would be invoked just before saving the entity.

2. Trigger Asynchronous Tasks Separately:
 • If you have “fire and forget” tasks (e.g., process_entity) that need to make external API calls or do lengthy processing, you might not want to embed them directly inside the immediate persistence workflow (especially if that workflow is meant to be synchronous and fast).
 • Instead, the workflow can update the entity to, say, include a “processing” flag or a URL/ID for later tracking, and then your endpoint (or a dedicated scheduler) can launch the async task.
 • This keeps the workflow focused on state update and leaves long-running operations in the asynchronous world.

In summary, yes—you can further decouple your controller such that it delegates non‐HTTP logic to workflow functions like process_companies_job. This makes the code more modular and robust. Just be mindful of whether the workflow function should remain synchronous (for quick, in–memory transformations) while longer async operations continue to run as separate background tasks.

By refactoring in this way, you ensure that:
 • The controller does not get cluttered with business logic.
 • The workflow function can encapsulate any immediate transformations or validations.
 • The asynchronous tasks remain separate, improving the maintainability and testability of each component.