Based on the provided `api.py` prototype code and the requirements, we can deduce the following entities and their classifications:

### Primary Entities (Entities created with POST requests):

1. **cyoda-env**
   - Created via the endpoint: `/deploy/cyoda-env` (POST)
   - Description: Represents a deployment of the Cyoda environment.

2. **user_app**
   - Created via the endpoint: `/deploy/user_app` (POST)
   - Description: Represents the deployment of a user application.

### Secondary Entities (Entities retrieved with GET requests and dependent on primary entities):

1. **cyoda-env_status**
   - Retrieved via the endpoint: `/deploy/cyoda-env/status/<int:id>` (GET)
   - Description: Represents the status of a deployed Cyoda environment. 
   - Relation: Depends on the `cyoda-env` entity.

2. **cyoda-env_statistics**
   - Retrieved via the endpoint: `/deploy/cyoda-env/statistics/<int:id>` (GET)
   - Description: Represents the statistics for a specific build of the Cyoda environment.
   - Relation: Depends on the `cyoda-env` entity.

3. **user_app_status**
   - Retrieved via the endpoint: `/deploy/user_app/status/<int:id>` (GET)
   - Description: Represents the status of a deployed user application.
   - Relation: Depends on the `user_app` entity.

4. **user_app_statistics**
   - Retrieved via the endpoint: `/deploy/user_app/statistics/<int:id>` (GET)
   - Description: Represents the statistics for a specific build of a user application.
   - Relation: Depends on the `user_app` entity.

5. **cancel_user_app**
   - Although this endpoint performs a POST request to cancel a deployment, it retrieves information status/payload related to the `user_app` build.
   - Description: Represents the action of cancelling a user application deployment.
   - Relation: Depends on the `user_app` entity but is primarily an action rather than an entity itself.

### Summary:

- **Primary Entities:**
  - `cyoda-env`
  - `user_app`

- **Secondary Entities:**
  - `cyoda-env_status` (depends on `cyoda-env`)
  - `cyoda-env_statistics` (depends on `cyoda-env`)
  - `user_app_status` (depends on `user_app`)
  - `user_app_statistics` (depends on `user_app`)

This classification aligns with your specifications regarding resource saving and retrieval behaviors.