Here’s a well-formatted summary of the final functional requirements for your application, including user stories, use cases, API endpoints, and request/response formats.

---

## Functional Requirements

### User Story 1: Deploy `cyoda-env`
- **As a user**, I want to deploy a `cyoda-env` so that I can manage environment configurations.
  - **Use Case**: Deploy `cyoda-env`
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

### User Story 2: Deploy `user-app`
- **As a user**, I want to deploy a `user-app` so that I can manage user-specific applications.
  - **Use Case**: Deploy `user-app`
    - **API Endpoint**: `POST /deploy/user_app`
    - **Request Format**:
      ```json
      {
        "repository_url": "http://....",
        "is_public": "true"
      }
      ```
    - **Response Format**:
      ```json
      {
        "build_id": "67890"
      }
      ```

### User Story 3: Check Status of `cyoda-env`
- **As a user**, I want to check the status of my `cyoda-env` deployment.
  - **Use Case**: Get `cyoda-env` status
    - **API Endpoint**: `GET /deploy/cyoda-env/status/{id}`
    - **Response Format**:
      ```json
      {
        "status": "running",
        "details": { ... }
      }
      ```

### User Story 4: Check Statistics of `cyoda-env`
- **As a user**, I want to check the statistics of my `cyoda-env` deployment.
  - **Use Case**: Get `cyoda-env` statistics
    - **API Endpoint**: `GET /deploy/cyoda-env/statistics/{id}`
    - **Response Format**:
      ```json
      {
        "statistics": { ... }
      }
      ```

### User Story 5: Check Status of `user-app`
- **As a user**, I want to check the status of my `user-app` deployment.
  - **Use Case**: Get `user-app` status
    - **API Endpoint**: `GET /deploy/user_app/status/{id}`
    - **Response Format**:
      ```json
      {
        "status": "completed",
        "details": { ... }
      }
      ```

### User Story 6: Check Statistics of `user-app`
- **As a user**, I want to check the statistics of my `user-app` deployment.
  - **Use Case**: Get `user-app` statistics
    - **API Endpoint**: `GET /deploy/user_app/statistics/{id}`
    - **Response Format**:
      ```json
      {
        "statistics": { ... }
      }
      ```

---

This structured format outlines the functional requirements clearly and should serve as a solid foundation for development. If you need any modifications or additional details, feel free to ask!