```markdown
# Functional Requirements for Deployment Management Application

## API Endpoints

### 1. Deploy Cyoda Environment
- **Endpoint**: `POST /deploy/cyoda-env`
- **Request Format**:
  ```json
  {
    "user_name": "test"
  }
  ```
- **Response Format**:
  ```json
  {
    "build_id": "12345",
    "status": "queued"
  }
  ```

### 2. Deploy User Application
- **Endpoint**: `POST /deploy/user_app`
- **Request Format**:
  ```json
  {
    "repository_url": "http://example.com/repo",
    "is_public": true,
    "user_name": "test"
  }
  ```
- **Response Format**:
  ```json
  {
    "build_id": "67890",
    "status": "queued"
  }
  ```

### 3. Get Cyoda Environment Deployment Status
- **Endpoint**: `GET /deploy/cyoda-env/status/{build_id}`
- **Response Format**:
  ```json
  {
    "build_id": "12345",
    "status": "running",
    "details": {
      "progress": "50%",
      "started_at": "2023-10-01T12:00:00Z"
    }
  }
  ```

### 4. Get Cyoda Environment Deployment Statistics
- **Endpoint**: `GET /deploy/cyoda-env/statistics/{build_id}`
- **Response Format**:
  ```json
  {
    "build_id": "12345",
    "statistics": {
      "duration": "10m",
      "success": true,
      "logs": "Log details here..."
    }
  }
  ```

### 5. Get User Application Deployment Status
- **Endpoint**: `GET /deploy/user_app/status/{build_id}`
- **Response Format**:
  ```json
  {
    "build_id": "67890",
    "status": "completed",
    "details": {
      "success": true,
      "ended_at": "2023-10-01T12:10:00Z"
    }
  }
  ```

### 6. Get User Application Deployment Statistics
- **Endpoint**: `GET /deploy/user_app/statistics/{build_id}`
- **Response Format**:
  ```json
  {
    "build_id": "67890",
    "statistics": {
      "duration": "15m",
      "success": false,
      "logs": "Error log details here..."
    }
  }
  ```

### 7. Cancel User Application Deployment
- **Endpoint**: `POST /deploy/cancel/user_app/{build_id}`
- **Request Format**:
  ```json
  {
    "comment": "Canceling a queued build",
    "readdIntoQueue": false
  }
  ```
- **Response Format**:
  ```json
  {
    "message": "Build cancelled successfully",
    "build_id": "67890"
  }
  ```

## User-App Interaction Diagram

```mermaid
sequenceDiagram
    participant User
    participant API as Backend API
    participant TeamCity as TeamCity Server

    User->>API: POST /deploy/cyoda-env {"user_name": "test"}
    API->>TeamCity: Trigger build with user_name
    TeamCity-->>API: Return build_id
    API-->>User: Return build_id and status

    User->>API: POST /deploy/user_app {"repository_url": "http://example.com/repo", "is_public": true, "user_name": "test"}
    API->>TeamCity: Trigger user application build
    TeamCity-->>API: Return build_id
    API-->>User: Return build_id and status

    User->>API: GET /deploy/cyoda-env/status/{build_id}
    API->>TeamCity: Fetch deployment status
    TeamCity-->>API: Return deployment status
    API-->>User: Return deployment status

    User->>API: GET /deploy/cyoda-env/statistics/{build_id}
    API->>TeamCity: Fetch deployment statistics
    TeamCity-->>API: Return statistics
    API-->>User: Return statistics

    User->>API: POST /deploy/cancel/user_app/{build_id} {"comment": "Canceling a queued build", "readdIntoQueue": false}
    API->>TeamCity: Cancel the build
    TeamCity-->>API: Confirm cancellation
    API-->>User: Return cancellation message
```
```