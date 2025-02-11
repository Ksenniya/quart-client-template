Here’s a well-formatted summary of the final functional requirements for your application, structured through user stories and use cases, along with the corresponding API endpoints.

### Functional Requirements

#### User Story 1: Deploy Cyoda Environment
- **As a user**, I want to deploy a Cyoda environment so that I can manage my environment configurations.
  
  **Use Case: Deploy Cyoda Environment**
  - **API Endpoint**: `POST /deploy/cyoda-env`
  - **Request Format**:
    ```json
    {
      "user_name": "test"
    }
    ```
  - **Response Format**:
    ```json
    {
      "build_id": "12345"
    }
    ```

#### User Story 2: Deploy User Application
- **As a user**, I want to deploy my application so that I can manage my application configurations.
  
  **Use Case: Deploy User Application**
  - **API Endpoint**: `POST /deploy/user_app`
  - **Request Format**:
    ```json
    {
      "repository_url": "http://example.com/my-repo",
      "is_public": "true"
    }
    ```
  - **Response Format**:
    ```json
    {
      "build_id": "67890"
    }
    ```

#### User Story 3: Check Deployment Status of Cyoda Environment
- **As a user**, I want to check the status of my Cyoda environment deployment so that I can monitor its progress.
  
  **Use Case: Get Cyoda Environment Status**
  - **API Endpoint**: `GET /deploy/cyoda-env/status/{id}`
  - **Response Format**:
    ```json
    {
      "status": "running",
      "details": "Deployment is in progress."
    }
    ```

#### User Story 4: Get Deployment Statistics for Cyoda Environment
- **As a user**, I want to retrieve statistics for my Cyoda environment deployment to understand its performance.
  
  **Use Case: Get Cyoda Environment Statistics**
  - **API Endpoint**: `GET /deploy/cyoda-env/statistics/{id}`
  - **Response Format**:
    ```json
    {
      "build_id": "12345",
      "duration": "5m",
      "success": true,
      "details": {
        "cpu_usage": "20%",
        "memory_usage": "512MB"
      }
    }
    ```

#### User Story 5: Check Deployment Status of User Application
- **As a user**, I want to check the status of my user application deployment so that I can monitor its progress.
  
  **Use Case: Get User Application Status**
  - **API Endpoint**: `GET /deploy/user_app/status/{id}`
  - **Response Format**:
    ```json
    {
      "status": "completed",
      "details": "Deployment completed successfully."
    }
    ```

#### User Story 6: Get Deployment Statistics for User Application
- **As a user**, I want to retrieve statistics for my user application deployment to understand its performance.
  
  **Use Case: Get User Application Statistics**
  - **API Endpoint**: `GET /deploy/user_app/statistics/{id}`
  - **Response Format**:
    ```json
    {
      "build_id": "67890",
      "duration": "10m