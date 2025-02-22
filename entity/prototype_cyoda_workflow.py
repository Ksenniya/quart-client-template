Yes, absolutely—we can (and should) move most of the asynchronous business logic from the controller into the workflow function. That allows controllers to remain thin, only handling request parsing and response formatting, while all the heavy lifting (data retrieval, filtering, enrichment, etc.) happens separately inside the workflow function. 

For example, in the companies search scenario, you can remove the fire‑and‑forget task from the endpoint and let the workflow (process_companies) do the following just before the entity is persisted:

• Retrieve companies from the external API (e.g., PRH),  
• Filter out inactive companies,  
• Enrich the companies with supplementary data (such as LEI) by calling asynchronous functions, and  
• Set the resulting state (status, completedAt, results, or error if needed) directly on the entity.

Because the workflow function supports asynchronous code, it’s a much cleaner solution than launching a separate background task. Remember, within this workflow function you must not call entity_service.add/update/delete for the current entity—instead, simply modify the entity object (e.g. entity["attribute"] = new_value) to affect its state; the new state will then be persisted by the entity_service. 

This design separates concerns: your controllers handle HTTP I/O while the workflow function encapsulates the business logic and any additional asynchronous processing (like fetching and enriching data). It also simplifies error handling and potential retries since all the processing logic is consolidated in one function. 

In summary, yes, moving the asynchronous tasks into process_{entity_name} is the right approach—it makes your codebase more maintainable, the controllers "lighter," and the asynchronous logic more directly tied to the persistence of the entity.