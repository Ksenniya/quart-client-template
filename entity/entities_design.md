Based on the provided prototype implementation in the `api.py` file, we can analyze the resources and associated entities that need to be created according to your specifications. Below is a breakdown of the necessary entities:

### Entities

1. **Primary Entities (POST requests)**:
   - **deploy_cyoda_env**: This endpoint saves a new deployment environment for Cyoda. It is associated with the `KubernetesPipeline_CyodaSaas` build type ID.
   - **deploy_user_app**: This endpoint saves a new deployment for a user application. It is associated with the `KubernetesPipeline_CyodaSaasUserEnv` build type ID.

2. **Secondary Entities (GET requests)**:
   - **get_cyoda_env_status**: This endpoint retrieves the deployment status of the Cyoda environment based on the provided `id`. It depends on the `deploy_cyoda_env` primary entity.
   - **get_cyoda_env_statistics**: This endpoint retrieves deployment statistics for the Cyoda environment based on the provided `id`. It also depends on the `deploy_cyoda_env` primary entity.
   - **get_user_app_status**: This endpoint retrieves the deployment status of the user application based on the provided `id`. It depends on the `deploy_user_app` primary entity.
   - **get_user_app_statistics**: This endpoint retrieves deployment statistics for the user application based on the provided `id`. It also depends on the `deploy_user_app` primary entity.

### Summary of Entities:

- **Primary Entities**:
  - `deploy_cyoda_env`
  - `deploy_user_app`

- **Secondary Entities**:
  - `get_cyoda_env_status` (depends on `deploy_cyoda_env`)
  - `get_cyoda_env_statistics` (depends on `deploy_cyoda_env`)
  - `get_user_app_status` (depends on `deploy_user_app`)
  - `get_user_app_statistics` (depends on `deploy_user_app`)

This structure meets the requirements outlined, where each POST resource corresponds to a primary entity and GET resources correspond to secondary entities depending on the respective primary entities.