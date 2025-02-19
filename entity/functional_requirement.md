Here are the final functional requirements for your application, presented in a clear and organized format:

---

## Functional Requirements

### 1. User Authentication
- **Description**: Users must authenticate to access deployment services.
- **User Story**: As a user, I want to authenticate using a Bearer token so that I can securely access the deployment services.
- **API Endpoint**: 
  - **POST /auth/token**
    - **Request**: 
      ```json
      {
        "username": "test_user",
        "password": "password123"
      }
      ```
    - **Response**: 
      ```json
      {
        "token": "your_bearer_token"
      }
      ```

### 2. Deployment Environment Management
- **Description**: Users can create and manage deployment environments.
- **User Story**: As a user, I want to create a deployment environment so that I can manage my application configurations.
- **API Endpoints**:
  - **POST /deploy/environments**
    - **Request**: 
      ```json
      {
        "user_name": "test"
      }
      ```
    - **Response**: 
      ```json
      {
        "build_id": "12345"
      }
      ```

  - **GET /deploy/environments/{id}/status**
    - **Response**: 
      ```json
      {
        "status": "running",
        "build_id": "12345"
      }
      ```

  - **GET /deploy/environments/{id}/statistics**
    - **Response**: 
      ```json
      {
        "build_id": "12345",
        "duration": "10m",
        "success": true
      }
      ```

### 3. User Application Deployment
- **Description**: Users can deploy their applications and check their status.
- **User Story**: As a user, I want to deploy my application so that it can be built and run in the specified environment.
- **API Endpoints**:
  - **POST /deploy/user-apps**
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
        "build_id": "67890"
      }
      ```

  - **GET /deploy/user-apps/{id}/status**
    - **Response**: 
      ```json
      {
        "status": "queued",
        "build_id": "67890"
      }
      ```

  - **GET /deploy/user-apps/{id}/statistics**
    - **Response**: 
      ```json
      {
        "build_id": "67890",
        "duration": "15m",
        "success": false
      }
      ```

### 4. Deployment Cancellation
- **Description**: Users can cancel their application deployments.
- **User Story**: As a user, I want to cancel my application deployment if needed.
- **API Endpoint**:
  - **POST /deploy/user-apps/{id}/cancel**
    - **Request**: 
      ```json
      {
        "comment": "Canceling a queued build",
        "readdIntoQueue": false
      }
      ```
    - **Response**: 
      ```json
      {
        "message": "Build canceled successfully."
      }
      ```

---

These functional requirements outline the core functionalities of your application and provide a clear path for development. If you have any further adjustments or requests, feel free to ask!