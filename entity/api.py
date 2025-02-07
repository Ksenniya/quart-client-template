Based on your functional requirements for the backend application that manages deployment and environment configuration for multiple users, here are the key entities that can be outlined:

1. **User**:
   - Represents the individual utilizing the application.
   - Attributes:
     - `user_id`: Unique identifier for the user.
     - `user_name`: Username of the user.
     - `token`: Authentication token for API access.

2. **Deployment**:
   - Represents the configuration and status of a build/deployment.
   - Attributes:
     - `deployment_id`: Unique identifier for each deployment.
     - `user_id`: ID of the user who initiated the deployment.
     - `build_type`: Type of build (e.g., "KubernetesPipeline_CyodaSaas", "KubernetesPipeline_CyodaSaasUserEnv").
     - `status`: Current status of the deployment (e.g., queued, running, succeeded, failed).
     - `properties`: Key-value pairs for user-defined properties (e.g., `user_defined_keyspace`, `user_defined_namespace`).

3. **Build**:
   - Represents a specific build within the build queue.
   - Attributes:
     - `build_id`: Identifier for the build.
     - `deployment_id`: ID of the deployment associated with the build.
     - `repository_url`: URL of the associated repository.
     - `is_public`: Boolean indicating if the build is public.
     
4. **Build Statistics**:
   - Represents performance and resource usage information regarding a build.
   - Attributes:
     - `build_id`: Identifier for the specific build.
     - `details`: A collection of statistics related to the build.
     
5. **Queue**:
   - Represents the queue of builds awaiting execution.
   - Attributes:
     - `builds`: List of `build` objects in the queue.
     - `total_count`: Total number of builds in the queue.

### Summary of Entities
- **User**: Handles authentication and permissions.
- **Deployment**: Manages deployment properties and statuses.
- **Build**: Represents individual builds within deployment configurations.
- **Build Statistics**: Provides insights into build performance and success metrics.
- **Queue**: Maintains the builds that are queued for execution.

These entities help define the structure of your application and will facilitate the implementation of the API's functionality in a cohesive manner. Each entity can also correlate with database tables or documents if you're using a database for persistence.