Here are the final functional requirements for your application, formatted clearly with user stories and use cases, including the necessary API endpoints, request/response formats, and a visual representation of user-app interaction.

### Functional Requirements

#### User Stories

1. **User Authentication**
   - **As a** user, **I want** to authenticate using a Bearer token from a separate service **so that** I can access the application securely.

2. **Manage Environment Deployment**
   - **As a** user, **I want** to create and manage deployment environments **so that** I can configure my application settings.

3. **Manage User Application Deployment**
   - **As a** user, **I want** to deploy my user application **so that** it can be built and run in the specified environment.

4. **Check Environment Deployment Status**
   - **As a** user, **I want** to check the status of my environment deployment **so that** I can monitor its progress.

5. **Check User Application Deployment Status**
   - **As a** user, **I want** to check the status of my user application deployment **so that** I can monitor its progress.

6. **Cancel Environment Deployment**
   - **As a** user, **I want** to cancel a queued environment deployment **so that** I can stop it if it is no longer needed.

7. **Cancel User Application Deployment**
   - **As a** user, **I want** to cancel a queued user application deployment **so that** I can stop it if it is no longer needed.

#### Use Cases

1. **User Authentication**
   - **API Endpoint**: (Handled by a separate service, no specific endpoint here)

2. **Manage Environment Deployment**
   - **API Endpoint**: `POST /environments`
   - **Request**:
     ```json
     {
       "user_name": "test_user"
     }
     ```
   - **Response**:
     ```json
     {
       "id": "env_id",
       "user_name": "test_user",
       "status": "created"
     }
     ```

3. **Manage User Application Deployment**
   - **API Endpoint**: `POST /user-applications`
   - **Request**:
     ```json
     {
       "repository_url": "http://example.com/repo.git",
       "is_public": true
     }
     ```
   - **Response**:
     ```json
     {
       "build_id": "build_id"
     }
     ```

4. **Check Environment Deployment Status**
   - **API Endpoint**: `GET /environments/status/{id}`
   - **Response**:
     ```json
     {
       "build_id": "build_id",
       "status": "in_progress",
       "details": "Deployment is currently in progress."
     }
     ```

5. **Check User Application Deployment Status**
   - **API Endpoint**: `GET /user-applications/status/{id}`
   - **Response**:
     ```json
     {
       "build_id": "build_id",
       "status": "completed",
       "details": "Deployment completed successfully."
     }
     ```

6. **Cancel Environment Deployment**
   - **API Endpoint**: `POST /environments/cancel/{id}`
   - **Request**:
     ```json
     {
       "comment":