Here’s a well-formatted summary of the functional requirements for your project, organized by user stories, use cases, and API endpoints.

---

## Functional Requirements

### User Story 1: Deploy Environment
- **As a** user,  
- **I want to** deploy a Cyoda environment,  
- **So that** I can configure my environment settings.

#### Use Case: Deploy Cyoda Environment
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

### User Story 2: Deploy User Application
- **As a** user,  
- **I want to** deploy a user application,  
- **So that** I can manage my application deployment.

#### Use Case: Deploy User Application
- **API Endpoint:** `POST /deploy/user_app`
  - **Request Format:**
    ```json
    {
      "repository_url": "http://....",
      "is_public": "true"
    }
    ```
  - **Response Format:**
    ```json
    {
      "build_id": "67890"
    }
    ```

### User Story 3: Check Deployment Status
- **As a** user,  
- **I want to** check the status of my deployments,  
- **So that** I can monitor their progress.

#### Use Case: Get Deployment Status
- **API Endpoint:** `GET /deploy/cyoda-env/status/{id}`
  - **Response Format:**
    ```json
    {
      "status": "running",
      "details": "Deployment is in progress."
    }
    ```

### User Story 4: Retrieve Deployment Statistics
- **As a** user,  
- **I want to** retrieve statistics for my deployments,  
- **So that** I can analyze their performance.

#### Use Case: Get Deployment Statistics
- **API Endpoint:** `GET /deploy/cyoda-env/statistics/{id}`
  - **Response Format:**
    ```json
    {
      "build_id": "12345",
      "success_rate": "95%",
      "duration": "30 minutes"
    }
    ```

---

This structured format provides a clear overview of the functional requirements for your application. If you need further modifications or additional details, just let me know!