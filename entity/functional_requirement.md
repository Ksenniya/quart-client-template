Here’s a structured approach to outline the functional requirements for your application, using user stories and use cases along with the necessary API endpoints. 

### User Stories

1. **User Authentication**
   - **As a** user, **I want to** authenticate using a Bearer token **so that** I can securely access the app functionalities.
   - **API Endpoint:** 
     - `POST /deploy/cyoda-env`
       - **Request:**
         ```json
         {
           "user_name": "test"
         }
         ```
       - **Response:**
         ```json
         {
           "success": true,
           "token": "Bearer <token>"
         }
         ```

2. **Trigger Environment Deployment**
   - **As a** user, **I want to** trigger a deployment to a specified environment **so that** the application is configured for my user.
   - **API Endpoint:** 
     - `POST /deploy/cyoda-env`
       - **Request:**
         ```json
         {
           "user_name": "test"
         }
         ```
       - **Response:**
         ```json
         {
           "build_id": 12345,
           "message": "Build triggered successfully"
         }
         ```

3. **Deploy User App**
   - **As a** user, **I want to** deploy a user-specific application **so that** I can manage my deployments.
   - **API Endpoint:**
     - `POST /deploy/user_app`
       - **Request:**
         ```json
         {
           "repository_url": "http://....",
           "is_public": "true"
         }
         ```
       - **Response:**
         ```json
         {
           "build_id": 67890,
           "message": "User app triggered for deployment"
         }
         ```

4. **Check Deployment Status**
   - **As a** user, **I want to** check the status of my environment deployment **so that** I can get updates on my builds.
   - **API Endpoint:**
     - `GET /deploy/cyoda-env/status/{id}`
       - **Response:**
         ```json
         {
           "status": "In Progress",
           "build_id": 12345
         }
         ```

5. **Fetch Deployment Statistics**
   - **As a** user, **I want to** get statistics of my deployments **so that** I can analyze the build performance.
   - **API Endpoint:**
     - `GET /deploy/cyoda-env/statistics/{id}`
       - **Response:**
         ```json
         {
           "build_id": 12345,
           "success_rate": 95,
           "total_builds": 20
         }
         ```

6. **Cancel Deployment**
   - **As a** user, **I want to** cancel an ongoing deployment **so that** I can avoid unwanted resources usage.
   - **API Endpoint:**
     - `POST /deploy/cancel/user_app/{id}`
       - **Request:**
         ```json
         {
           "comment": "Canceling a queued build",
           "readdIntoQueue": false
         }
         ```
       - **Response:**
         ```json
         {
           "success": true,
           "message": "Build canceled successfully"
         }
         ```

### Use Cases

1. **Use Case: User Authentication**
   - **Actors:** User
   - **Preconditions:** User must have valid credentials.
   - **Flow:**
     1. User sends authentication request to `POST /deploy/cyoda-env`.
     2. The system verifies the user and returns a Bearer token.

2. **Use Case: Trigger Environment Deployment**
   - **Actors:** User
   - **Preconditions:** User must be authenticated with a Bearer token.
   - **Flow:**
     1. User sends a request to `POST /deploy/cyoda-env` with user name.
     2. The system triggers the build in TeamCity and returns the build ID.

3. **Use Case: Deploy User App**
   - **Actors:** User
   - **Preconditions:** User must be authenticated with a Bearer token.
   - **Flow:**
     1. User sends a request to `POST /deploy/user_app` with repository URL and visibility.
     2. The system triggers the build and returns the build ID.

4. **Use Case: Check Deployment Status**
   - **Actors:** User
   - **Preconditions:** User must have a valid build ID.
   - **Flow:**
     1. User sends a request to `GET /deploy/cyoda-env/status/{id}`.
     2. The system returns the current status of the deployment.

5. **Use Case: Fetch Deployment Statistics**
   - **Actors:** User
   - **Preconditions:** User must have a valid build ID.
   - **Flow:**
     1. User sends a request to `GET /deploy/cyoda-env/statistics/{id}`.
     2. The system returns statistics related to the deployment.

6. **Use Case: Cancel Deployment**
   - **Actors:** User
   - **Preconditions:** User must have a valid build ID.
   - **Flow:**
     1. User sends a request to `POST /deploy/cancel/user_app/{id}` with a comment.
     2. The system cancels the build and returns a success message.

### Mermaid Diagram

```mermaid
graph TD;
    A[User] -->|Auth with token| B[API: /deploy/cyoda-env]
    B --> C{Token Valid}
    C -->|Yes| D[API: Trigger Deployment]
    C -->|No| E[Error: Invalid Credentials]

    D -->|Trigger| F[API: /deploy/cyoda-env]
    F --> G[Return Build ID]

    A -->|Check Status| H[API: /deploy/cyoda-env/status/{id}]
    H --> I[Return Deployment Status]

    A -->|Fetch Statistics| J[API: /deploy/cyoda-env/statistics/{id}]
    J --> K[Return Statistics]

    A -->|Cancel Deployment| L[API: /deploy/cancel/user_app/{id}]
    L --> M[Return Success]
```

This structure outlines your functional requirements clearly with user stories, API endpoints, request/response formats, and a visual representation of user-app interaction. If further iterations are needed, we can expand on this base.