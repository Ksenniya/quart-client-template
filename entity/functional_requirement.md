Here is the well-formatted final functional requirements document for your application, including user stories, use cases, API endpoints, and response formats.

---

## Functional Requirements Document

### Overview
This document outlines the functional requirements for an application that manages deployment and environment configuration for multiple users. The application will facilitate two types of deployments: environment configurations and user applications. Each deployment type will have its own API endpoints for deployment, status checks, and statistics retrieval.

### User Stories

1. **Deploy Environment Configuration**
   - **As a user**, I want to deploy an environment configuration so that I can manage the application settings related to the environment.

2. **Deploy User Application**
   - **As a user**, I want to deploy my application from a repository so that I can run it in my environment.

3. **Check Environment Deployment Status**
   - **As a user**, I want to check the status of my environment deployments so that I can monitor their progress.

4. **Check User Application Deployment Status**
   - **As a user**, I want to check the status of my user application deployments so that I can monitor their progress.

5. **Retrieve Environment Deployment Statistics**
   - **As a user**, I want to retrieve statistics for my environment deployments so that I can analyze their performance.

6. **Retrieve User Application Deployment Statistics**
   - **As a user**, I want to retrieve statistics for my user application deployments so that I can analyze their performance.

### Use Cases

#### Use Case 1: Deploy Environment Configuration
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

#### Use Case 2: Deploy User Application
- **API Endpoint**: `POST /deploy/user_app`
- **Request Format**:
  ```json
  {
      "repository_url": "http://example.com/repo.git",
      "is_public": "true"
  }
  ```
- **Response Format**:
  ```json
  {
      "build_id": "67890"
  }
  ```

#### Use Case 3: Check Environment Deployment Status
- **API Endpoint**: `GET /deploy/cyoda-env/status/{id}`
- **Response Format**:
  ```json
  {
      "status": "running",
      "build_id": "12345"
  }
  ```

#### Use Case 4: Check User Application Deployment Status
- **API Endpoint**: `GET /deploy/user_app/status/{id}`
- **Response Format**:
  ```json
  {
      "status": "running",
      "build_id": "67890"
  }
  ```

#### Use Case 5: Retrieve Environment Deployment Statistics
- **API Endpoint**: `GET /deploy/cyoda-env/statistics/{id}`
- **Response Format**:
  ```json
  {
      "build_id": "12345",
      "statistics": {
          "duration": "5m",
          "success": true
      }
  }
  ```

#### Use Case 6: Retrieve User Application Deployment Statistics
- **API Endpoint**: `GET /deploy/user_app/statistics/{id}`
- **Response Format**:
  ```json
