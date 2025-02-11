Here’s a well-structured and formatted presentation of the final functional requirements for your application, including user stories, use cases, and API specifications:

### Functional Requirements

---

#### User Story 1: Deploy Cyoda Environment
- **As a** user,
- **I want** to deploy a Cyoda environment,
- **So that** I can manage my deployment configurations.

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

---

#### User Story 2: Deploy User Application
- **As a** user,
- **I want** to deploy a user application,
- **So that** I can manage my application deployments.

**Use Case: Deploy User Application**
- **API Endpoint**: `POST /deploy/user_app`
- **Request Format**:
  ```json
  {
    "repository_url": "http://example.com/repo",
    "is_public": "true"
  }
  ```
- **Response Format**:
  ```json
  {
    "build_id": "67890"
  }
  ```

---

#### User Story 3: Check Deployment Status
- **As a** user,
- **I want** to check the status of my Cyoda environment deployment,
- **So that** I can monitor its progress.

**Use Case: Get Cyoda Environment Status**
- **API Endpoint**: `GET /deploy/cyoda-env/status/{id}`
- **Response Format**:
  ```json
  {
    "status": "running",
    "details": "Deployment is in progress."
  }
  ```

---

#### User Story 4: Get Deployment Statistics
- **As a** user,
- **I want** to retrieve statistics for my Cyoda environment deployment,
- **So that** I can analyze its performance.

**Use Case: Get Cyoda Environment Statistics**
- **API Endpoint**: `GET /deploy/cyoda-env/statistics/{id}`
- **Response Format**:
  ```json
  {
    "statistics": {
      "duration": "5m",
      "success_rate": "95%"
    }
  }
  ```

---

#### User Story 5: Check User Application Status
- **As a** user,
- **I want** to check the status of my user application deployment,
- **So that** I can monitor its progress.

**Use Case: Get User Application Status**
- **API Endpoint**: `GET /deploy/user_app/status/{id}`
- **Response Format**:
  ```json
  {
    "status": "completed",
    "details": "Deployment was successful."
  }
  ```

---

#### User Story 6: Get User Application Statistics
- **As a** user,
- **I want** to retrieve statistics for my user application deployment,
- **So that** I can analyze its performance.

**Use Case: Get User Application Statistics**
- **API Endpoint**: `GET /deploy/user_app/statistics/{id}`
- **Response Format**:
  ```json
  {
    "statistics": {
      "duration": "3m",
      "success_rate": "90