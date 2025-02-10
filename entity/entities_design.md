Based on your requirements and the provided Python `api.py` code using the Quart framework, we can identify the following entities:

### Primary Entities (Resources Saved with POST and Require Workflows)
1. **deploy_cyoda_env**
   - Endpoint: `/deploy/cyoda-env`
   - Description: Initiates the deployment of the Cyoda environment based on the provided user name.

2. **deploy_user_app**
   - Endpoint: `/deploy/user_app`
   - Description: Initiates the deployment of a user-specific application based on the provided repository URL and public status.

3. **cancel_user_app**
   - Endpoint: `/deploy/cancel/user_app/<id>`
   - Description: Cancels the queued build of the user app based on the provided build ID.

### Secondary Entities (Resources Retrieved with GET, Depend on Primary Entities)
1. **cyoda_env_status**
   - Endpoint: `/deploy/cyoda-env/status/<id>`
   - Description: Fetches the status of the Cyoda environment deployment using the build ID.
   - Depends on: `deploy_cyoda_env`
  
2. **cyoda_env_statistics**
   - Endpoint: `/deploy/cyoda-env/statistics/<id>`
   - Description: Retrieves statistics for the Cyoda environment deployment using the build ID.
   - Depends on: `deploy_cyoda_env`

3. **user_app_status**
   - Endpoint: `/deploy/user_app/status/<id>`
   - Description: Fetches the status of the user application deployment using the build ID.
   - Depends on: `deploy_user_app`
  
4. **user_app_statistics**
   - Endpoint: `/deploy/user_app/statistics/<id>`
   - Description: Retrieves statistics for the user application deployment using the build ID.
   - Depends on: `deploy_user_app`

### Summary
- **Primary Entities**: `deploy_cyoda_env`, `deploy_user_app`, `cancel_user_app`
- **Secondary Entities**: `cyoda_env_status`, `cyoda_env_statistics`, `user_app_status`, `user_app_statistics`

This structure allows you to establish the relationships between entities as per your specifications. Each primary entity corresponds to a resource that can be created and requires a workflow, whereas the secondary entities are reads that depend on the primary entities for context.