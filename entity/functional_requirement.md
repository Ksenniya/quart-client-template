Here are the well-formatted final functional requirements for your backend application, including user stories, API endpoints, request/response formats, and visual representations:

---

## Functional Requirements for Deployment Application

### User Stories

1. **User Authentication**
   - **As a user**, I want to authenticate myself so that I can access the deployment features securely.
   - **API Endpoint**: `POST /auth/login`
     - **Request**: 
       ```json
       {
         "username": "string",
         "password": "string"
       }
       ```
     - **Response**: 
       ```json
       {
         "token": "string",
         "message": "Login successful"
       }
       ```

2. **Create Environment**
   - **As a user**, I want to create a deployment environment so that I can manage my applications.
   - **API Endpoint**: `POST /environments`
     - **Request**: 
       ```json
       {
         "user_name": "string",
         "env_config": "string"
       }
       ```
     - **Response**: 
       ```json
       {
         "build_id": "mock_build_id",
         "message": "Environment created successfully"
       }
       ```

3. **Deploy Application**
   - **As a user**, I want to deploy my application to a specified environment.
   - **API Endpoint**: `POST /deployments`
     - **Request**: 
       ```json
       {
         "repository_url": "string",
         "is_public": "boolean"
       }
       ```
     - **Response**: 
       ```json
       {
         "build_id": "mock_build_id",
         "message": "Deployment initiated"
       }
       ```

4. **Get Environment Status**
   - **As a user**, I want to check the status of my deployment environment.
   - **API Endpoint**: `GET /environments/{id}/status`
     - **Response**: 
       ```json
       {
         "status": "string",
         "repository_url": "string",
         "is_public": "boolean"
       }
       ```

5. **Get Environment Statistics**
   - **As a user**, I want to retrieve statistics for my deployment environment.
   - **API Endpoint**: `GET /environments/{id}/statistics`
     - **Response**: 
       ```json
       {
         "statistics": "object"
       }
       ```

6. **Cancel Deployment**
   - **As a user**, I want to cancel an ongoing deployment.
   - **API Endpoint**: `POST /deployments/{id}/cancel`
     - **Request**: 
       ```json
       {
         "comment": "string",
         "readdIntoQueue": "boolean"
       }
       ```
     - **Response**: 
       ```json
       {
         "message": "Build canceled successfully"
       }
       ```

### Visual Representation

#### User Journey Diagram

```mermaid
journey
    title User Journey for Deployment Application
    section User Authentication
      User logs in: 5: User
      User receives token: 5: System
    section Create Environment
      User creates environment: 5: User
      System stores environment: 5: System
    section Deploy Application
      User initiates deployment: 5: User
      System processes deployment: 5: System
    section Check Status
      User requests status: 5: User
      System returns status: 5: System
    section Cancel Deployment
      User cancels deployment: 5: User
      System confirms cancellation: 5: System
```

#### Sequence Diagram for Deployment Process

```mermaid
sequenceDiagram
    participant User
    participant API
    participant TeamCity

    User->>API: POST /auth/login
    API->>User: Returns token

    User->>API: POST /environments
    API->>TeamCity: Mock API call to create environment
    TeamCity-->>API: Returns build_id
    API->>User: Returns build_id

    User->>API: POST /deployments
    API->>TeamCity: Mock API call to deploy application
    TeamCity-->>API: Returns build_id
    API->>User: Returns deployment message

    User->>API: GET /environments/{id}/status
    API->>TeamCity: Mock API call to get status
    TeamCity-->>API: Returns status
    API->>User: Returns status

    User->>API: POST /deployments/{id}/cancel
    API->>TeamCity: Mock API call to cancel deployment
    TeamCity-->>API: Returns cancellation confirmation
    API->>User: Returns cancellation message
```

---

This document outlines the necessary functional requirements for your application and provides clear guidance for development. Let me know if you need any further assistance or modifications!