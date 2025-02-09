Here are the functional requirements structured as user stories and use cases, along with necessary API endpoints and example request/response formats. Additionally, I've included Mermaid diagrams to represent the user-app interaction visually.

### User Stories

1. **User Authentication**
   - As a user, I want to authenticate using a Bearer token to access the deployment APIs.

   **API Endpoint:**
   - **POST /deploy/cyoda-env**
     - Request:
       ```json
       {
           "user_name": "test"
       }
       ```
     - Response:
       ```json
       {
           "access_token": "Bearer <token>",
           "user_name": "test"
       }
       ```

2. **Submit Deployment for Environment Configuration**
   - As a user, I want to submit a request to deploy an environment configuration using my username.

   **API Endpoint:**
   - **POST /deploy/cyoda-env**
     - Request:
       ```json
       {
           "user_name": "test"
       }
       ```
     - Response:
       ```json
       {
           "build_id": "12345"
       }
       ```

3. **Submit User Application Deployment**
   - As a user, I want to deploy my application by providing a repository URL and a visibility setting.

   **API Endpoint:**
   - **POST /deploy/user_app**
     - Request:
       ```json
       {
           "repository_url": "http://example.com/repo.git",
           "is_public": true
       }
       ```
     - Response:
       ```json
       {
           "build_id": "67890"
       }
       ```

4. **Check Status of Environment Configuration Deployment**
   - As a user, I want to check the status of my environment deployment using a build ID.

   **API Endpoint:**
   - **GET /deploy/cyoda-env/status/{id}**
     - Response:
       ```json
       {
           "build_id": "12345",
           "status": "running",
           "repository_url": "http://example.com/repo.git",
           "is_public": true
       }
       ```

5. **Get Statistics for Environment Deployment**
   - As a user, I want to retrieve statistics for my environment deployment using a build ID.

   **API Endpoint:**
   - **GET /deploy/cyoda-env/statistics/{id}**
     - Response:
       ```json
       {
           "build_id": "12345",
           "statistics": {
               // statistics data here
           }
       }
       ```

6. **Check Status of User Application Deployment**
   - As a user, I want to check the status of my user application deployment using a build ID.

   **API Endpoint:**
   - **GET /deploy/user_app/status/{id}**
     - Response:
       ```json
       {
           "build_id": "67890",
           "status": "success",
           "repository_url": "http://example.com/repo.git",
           "is_public": true
       }
       ```

7. **Get Statistics for User Application Deployment**
   - As a user, I want to retrieve statistics for my user application deployment.

   **API Endpoint:**
   - **GET /deploy/user_app/statistics/{id}**
     - Response:
       ```json
       {
           "build_id": "67890",
           "statistics": {
               // statistics data here
           }
       }
       ```

8. **Cancel a User Application Deployment**
   - As a user, I want to cancel my user application deployment using a build ID.

   **API Endpoint:**
   - **POST /deploy/cancel/user_app/{id}**
     - Request:
       ```json
       {
           "comment": "Canceling a queued build",
           "readdIntoQueue": false
       }
       ```
     - Response:
       ```json
       {
           "message": "Build canceled successfully."
       }
       ```

### Mermaid Diagrams

Here’s a visual representation of user interactions using the Mermaid syntax:

```mermaid
graph TD;
    A[User] --> B[POST /deploy/cyoda-env]
    B --> C{Authenticate}
    C -->|Success| D[Receive Bearer Token]
    
    D --> E[POST /deploy/cyoda-env]
    E --> F{Submit Env Config}
    F -->|Success| G[Receive build_id]
    
    D --> H[GET /deploy/cyoda-env/status/{id}]
    H --> I{Get Status}
    
    D --> J[GET /deploy/cyoda-env/statistics/{id}]
    J --> K{Get Statistics}
    
    D --> L[POST /deploy/user_app]
    L --> M{Submit User App}
    M -->|Success| N[Receive build_id]

    D --> O[GET /deploy/user_app/status/{id}]
    O --> P{Get User App Status}
    
    D --> Q[GET /deploy/user_app/statistics/{id}]
    Q --> R{Get User App Statistics}
    
    D --> S[POST /deploy/cancel/user_app/{id}]
    S --> T{Cancel User App}
```

### Summary

These functional requirements should give a clear structure for your application's API design. Each user story and associated use case outline not only the functional aspects but also the interaction flow between users and the backend services.