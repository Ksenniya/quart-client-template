Here’s a structured approach to defining the functional requirements for your project in terms of user stories, use cases, API endpoints, and visual representations using Mermaid diagrams:

### Functional Requirements

#### User Stories and Use Cases

1. **User Story: User Authentication**
   - **As a** user,
   - **I want** to authenticate using a Bearer token,
   - **So that** I can access the deployment and environment configuration features.

   **Use Case: Authenticate User**
   - **Endpoint:** `POST /deploy/cyoda-env`
   - **Request:**
     ```json
     {
       "user_name": "test"
     }
     ```
   - **Response:**
     ```json
     {
       "token": "your_auth_token",
       "message": "Authenticated successfully"
     }
     ```

2. **User Story: Deploy Environment Configuration**
   - **As a** user,
   - **I want** to deploy an environment configuration,
   - **So that** I can manage specific user environments.

   **Use Case: Deploy Environment**
   - **Endpoint:** `POST /deploy/cyoda-env`
   - **Request:**
     ```json
     {
       "user_name": "test"
     }
     ```
   - **Action:** Trigger a build on TeamCity
   - **Response:**
     ```json
     {
       "build_id": 12345
     }
     ```

3. **User Story: Deploy User Application**
   - **As a** user,
   - **I want** to deploy a specific user application,
   - **So that** I can manage my application deployments.

   **Use Case: Deploy User App**
   - **Endpoint:** `POST /deploy/user_app`
   - **Request:**
     ```json
     {
       "repository_url": "http://....",
       "is_public": "true"
     }
     ```
   - **Action:** Trigger a build on TeamCity
   - **Response:**
     ```json
     {
       "build_id": 67890
     }
     ```

4. **User Story: Check Deployment Status**
   - **As a** user,
   - **I want** to check the status of my deployed environment,
   - **So that** I can understand if the deployment was successful.

   **Use Case: Get Deployment Status**
   - **Endpoint:** `GET /deploy/cyoda-env/status/{id}`
   - **Response:**
     ```json
     {
       "status": "In Progress/Success/Failure",
       "build_id": "{id}",
       "details": "Deploying..."
     }
     ```

5. **User Story: Get Deployment Statistics**
   - **As a** user,
   - **I want** to view the statistics of my deployments,
   - **So that** I can measure the performance and success rate.

   **Use Case: Get Deployment Statistics**
   - **Endpoint:** `GET /deploy/cyoda-env/statistics/{id}`
   - **Response:**
     ```json
     {
       "build_id": "{id}",
       "statistics": {
         "duration": "120s",
         "status": "Success"
       }
     }
     ```

6. **User Story: Cancel Deployment**
   - **As a** user,
   - **I want** to cancel a specific user application deployment,
   - **So that** I can stop a deployment that is no longer needed.

   **Use Case: Cancel User App**
   - **Endpoint:** `POST /deploy/cancel/user_app/{id}`
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
       "message": "Build with ID {id} has been canceled"
     }
     ```

### Visual Representations

Here are the Mermaid diagrams to represent the user-app interactions for the critical functionalities.

```mermaid
graph TD;
    A[User] -->|Authenticate| B(API Gateway);
    B -->|POST /deploy/cyoda-env| C[Auth Service];
    C --> D[Return Token];

    A -->|Deploy Environment| B;
    B -->|POST /deploy/cyoda-env| E[Deployment Service];
    E --> F[Trigger Build];

    A -->|Deploy User App| B;
    B -->|POST /deploy/user_app| G[User App Service];
    G --> H[Trigger User Build];

    A -->|Check Environment Status| B;
    B -->|GET /deploy/cyoda-env/status/{id}| I[Status Service];
    I --> J[Return Deployment Status];

    A -->|Get Deployment Statistics| B;
    B -->|GET /deploy/cyoda-env/statistics/{id}| K[Statistics Service];
    K --> L[Return Statistics];

    A -->|Cancel Deployment| B;
    B -->|POST /deploy/cancel/user_app/{id}| M[Cancel Service];
    M --> N[Return Cancellation Status];
```

These structured functional requirements, user stories, use cases, API endpoints, and visual representations should guide your application development effectively. Please review and let me know if you have any additional functionality or details needed.