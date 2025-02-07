For your backend application that manages deployment and environment configuration for multiple users, the minimum number of required entities would likely include the following:

1. **User**:
   - Attributes could include:
     - `user_id`: A unique identifier for the user.
     - `user_name`: The name of the user.
     - `email`: The email address of the user (if needed for notifications or account management).
     - `token`: A bearer token for authentication.

2. **Build**:
   - Attributes could include:
     - `build_id`: A unique identifier for the build.
     - `build_type`: The type of the build (e.g., KubernetesPipeline_CyodaSaas).
     - `user_defined_keyspace`: A user-defined keyspace for the build.
     - `user_defined_namespace`: A user-defined namespace for the build.
     - `status`: The current status of the build (e.g., queued, running, completed, failed, canceled).
     - `created_at`: Timestamp of when the build was created.
     - `updated_at`: Timestamp of the last update to the build.

3. **Environment** (optional but recommended):
   - Attributes could include:
     - `env_id`: A unique identifier for the environment.
     - `env_name`: A name for the environment (e.g., "Development", "Production").
     - `repository_url`: The URL of the repository associated with the environment.
     - `is_public`: A boolean indicating whether the environment is public.

4. **Deployment** (optional but helpful):
   - Attributes could include:
     - `deployment_id`: A unique identifier for the deployment.
     - `build_id`: A reference to the associated build.
     - `env_id`: A reference to the environment where this deployment is taking place.
     - `status`: The status of the deployment (e.g., successful, failed, in-progress).

### Minimum Required Entities

In summary, the minimum entities you would need for your application would be User and Build. The Environment and Deployment entities can be added later based on your application’s requirements and complexity. This initial set of entities should be sufficient to manage authentication and the basic functionalities required for handling builds and their configurations for users.