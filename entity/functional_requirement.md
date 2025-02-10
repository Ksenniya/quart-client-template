Here's a structured breakdown of the functional requirements for your application with user stories, use cases, and definitions of necessary API endpoints, including request/response formats. Also included is a visual representation using Mermaid diagrams.

### User Stories:

#### User Story 1: Manage Cyoda Environment
**As a** user,  
**I want to** create or update a deployment in the Cyoda environment,  
**So that** my application can be configured for my user environment.

**Use Cases:**
1. **Create/Update Cyoda Environment**
   - **API Endpoint:** `POST /deploy/cyoda-env`
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

2. **Get Status of Cyoda Environment Deployment**
   - **API Endpoint:** `GET /deploy/cyoda-env/status/{id}`
   - **Response Format:**
     ```json
     {
       "status": "success",
       "details": {
         "repository_url": "http://....",
         "is_public": "true"
       }
     }
     ```

3. **Get Statistics of Cyoda Environment Deployment**
   - **API Endpoint:** `GET /deploy/cyoda-env/statistics/{id}`
   - **Response Format:**
     ```json
     {
       "statistics": {...}  // Details specific statistics related to the build
     }
     ```

#### User Story 2: Manage User Application
**As a** user,  
**I want to** deploy my user-specific application,  
**So that** I can work with my own environment configuration.

**Use Cases:**
1. **Create/Update User Application**
   - **API Endpoint:** `POST /deploy/user_app`
   - **Request Format:**
     ```json
     {
       "repository_url": "http://....",
       "is_public": true
     }
     ```
   - **Response Format:**
     ```json
     {
       "build_id": "67890"
     }
     ```

2. **Get Status of User Application Deployment**
   - **API Endpoint:** `GET /deploy/user_app/status/{id}`
   - **Response Format:**
     ```json
     {
       "status": "success",
       "details": {
         "repository_url": "http://....",
         "is_public": "true"
       }
     }
     ```

3. **Get Statistics of User Application Deployment**
   - **API Endpoint:** `GET /deploy/user_app/statistics/{id}`
   - **Response Format:**
     ```json
     {
       "statistics": {...}  // Details specific statistics related to the build
     }
     ```

4. **Cancel User Application Deployment**
   - **API Endpoint:** `POST /deploy/cancel/user_app/{id}`
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

### Mermaid Diagram:

Here's a visual representation of the user-app interaction using Mermaid.

```mermaid
graph TD
    User -->|POST /deploy/cyoda-env| Backend
    Backend -->|Build ID| User
    User -->|GET /deploy/cyoda-env/status/{id}| Backend
    Backend -->|Status| User
    User -->|GET /deploy/cyoda-env/statistics/{id}| Backend
    Backend -->|Statistics| User
    User -->|POST /deploy/user_app| Backend
    Backend -->|Build ID| User
    User -->|GET /deploy/user_app/status/{id}| Backend
    Backend -->|Status| User
    User -->|GET /deploy/user_app/statistics/{id}| Backend
    Backend -->|Statistics| User
    User -->|POST /deploy/cancel/user_app/{id}| Backend
    Backend -->|Cancel Result| User
```

### Conclusion

This functional requirements document outlines the user stories and their respective use cases along with the API specifications necessary for your backend application. The Mermaid diagram visually represents the interaction between users and the application. Please feel free to reach out for any modifications or additional details!