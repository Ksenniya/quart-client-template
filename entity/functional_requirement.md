Here is a well-structured presentation of the final functional requirements for your application, including user stories, use cases, API endpoints, request/response formats, and visual representations using Mermaid diagrams.

### Functional Requirements

#### User Stories

1. **User Story 1: User Authentication**
   - **As a** user, 
   - **I want to** authenticate using a Bearer token, 
   - **So that** I can access the deployment features of the application.

   - **API Endpoint:**
     - **POST** `/deploy/cyoda-env`
   - **Request Format:**
     ```json
     {
       "user_name": "test"
     }
     ```
   - **Response Format:**
     ```json
     {
       "token": "Bearer <token>"
     }
     ```

2. **User Story 2: Deploy Cyoda Environment**
   - **As a** user,
   - **I want to** deploy a Cyoda environment,
   - **So that** I can manage my Kubernetes applications.

   - **API Endpoint:**
     - **POST** `/deploy/cyoda-env`
   - **Request Format:**
     ```json
     {
       "user_name": "test"
     }
     ```
   - **Response Format:**
     ```json
     {
       "build_id": "12345"
     }
     ```

3. **User Story 3: Deploy User Application**
   - **As a** user,
   - **I want to** deploy my user application,
   - **So that** I can manage my application’s deployment.

   - **API Endpoint:**
     - **POST** `/deploy/user_app`
   - **Request Format:**
     ```json
     {
       "repository_url": "http://example.com/user_app",
       "is_public": "true"
     }
     ```
   - **Response Format:**
     ```json
     {
       "build_id": "67890"
     }
     ```

4. **User Story 4: Get Deployment Status**
   - **As a** user,
   - **I want to** check the status of a deployment,
   - **So that** I can monitor its progress.

   - **API Endpoint:**
     - **GET** `/deploy/cyoda-env/status/{id}`
   - **Response Format:**
     ```json
     {
       "status": "In Progress",
       "details": "Deployment is ongoing."
     }
     ```

5. **User Story 5: Get Deployment Statistics**
   - **As a** user,
   - **I want to** retrieve deployment statistics,
   - **So that** I can analyze performance and resources.

   - **API Endpoint:**
     - **GET** `/deploy/cyoda-env/statistics/{id}`
   - **Response Format:**
     ```json
     {
       "statistics": {
         // statistic details here
       }
     }
     ```

6. **User Story 6: Cancel User Application Deployment**
   - **As a** user,
   - **I want to** cancel a queued deployment,
   - **So that** I can stop unnecessary processes.

   - **API Endpoint:**
     - **POST** `/deploy/cancel/user_app/{id}`
   - **Request Format:**
     ```json
     {
       "comment": "Canceling a queued build",
       "readdIntoQueue": false
     }
     ```
   - **Response Format:**
     ```json
     {
       "message": "Build canceled successfully."
     }
     ```

#### Use Cases

1. **Use Case for User Authentication**
   - **Actors:** User
   - **Preconditions:** User has credentials to authenticate.
   - **Postconditions:** User receives a Bearer token for subsequent API calls.
   - **Main Flow:**
     1. User sends a POST request to `/deploy/cyoda-env` with user_name in the body.
     2. Application validates the user and responds with a Bearer token.

2. **Use Case for Deploying Cyoda Environment**
   - **Actors:** User
   - **Preconditions:** User is authenticated.
   - **Postconditions:** Environment deployment is initiated.
   - **Main Flow:**
     1. User sends a POST request to `/deploy/cyoda-env`.
     2. Application queues the deployment and returns the build ID.

3. **Use Case for Checking Deployment Status**
   - **Actors:** User
   - **Preconditions:** User is authenticated and has initiated a deployment.
   - **Postconditions:** User receives the current status of the deployment.
   - **Main Flow:**
     1. User sends a GET request to `/deploy/cyoda-env/status/{id}`.
     2. Application retrieves and returns the deployment status.

### Mermaid Diagram Representation

```mermaid
graph TD;
    User-->Authenticates[POST /deploy/cyoda-env]
    Authenticates-->Token[Returns Token]
    User-->DeploysEnv[POST /deploy/cyoda-env]
    DeploysEnv-->BuildID[Returns build ID]
    User-->ChecksStatus[GET /deploy/cyoda-env/status/{id}]
    ChecksStatus-->Status[Returns status]
    User-->CancelsDeployment[POST /deploy/cancel/user_app/{id}]
    CancelsDeployment-->CancelMessage[Returns success message]
```

This structured format includes user stories and use cases paired with detailed API specifications that can guide the development process. This approach will help you to communicate requirements clearly with your development team, ensure completeness, and create a solid foundation for your application.