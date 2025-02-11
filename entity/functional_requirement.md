Here are the final functional requirements for your project, presented in a well-structured format.

### Functional Requirements

#### 1. User Deployment of Cyoda Environment
- **User Story**: As a user, I want to deploy a Cyoda environment so that I can manage my environment configurations.
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

#### 2. User Deployment of User Application
- **User Story**: As a user, I want to deploy my application so that I can manage my application configurations.
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

#### 3. Check Status of Cyoda Environment Deployment
- **User Story**: As a user, I want to check the status of my Cyoda environment deployment.
- **API Endpoint**: `GET /deploy/cyoda-env/status/{id}`
  - **Response Format**:
    ```json
    {
        "status": "running",
        "details": "Deployment is in progress."
    }
    ```

#### 4. Get Statistics for Cyoda Environment Deployment
- **User Story**: As a user, I want to retrieve statistics for my Cyoda environment deployment.
- **API Endpoint**: `GET /deploy/cyoda-env/statistics/{id}`
  - **Response Format**:
    ```json
    {
        "statistics": {
            "success_rate": 95,
            "duration": "10m",
            "errors": 0
        }
    }
    ```

#### 5. Check Status of User Application Deployment
- **User Story**: As a user, I want to check the status of my user application deployment.
- **API Endpoint**: `GET /deploy/user_app/status/{id}`
  - **Response Format**:
    ```json
    {
        "status": "completed",
        "details": "Deployment completed successfully."
    }
    ```

#### 6. Get Statistics for User Application Deployment
- **User Story**: As a user, I want to retrieve statistics for my user application deployment.
- **API Endpoint**: `GET /deploy/user_app/statistics/{id}`
  - **Response Format**:
    ```json
    {
        "statistics": {
            "success_rate": 90,
            "duration": "15m",
            "errors": 1
        }
    }
    ```

### Additional Considerations
- **Error Handling**: Define standardized error responses for various failure scenarios (e.g., invalid input, deployment failures).
- **Logging**: Implement logging for API requests and interactions with TeamCity to monitor usage and troubleshoot issues.
- **Future Scalability**: Keep in mind potential future user-specific configurations, notifications, or integrations.

This structured approach should help in the subsequent phases of the project, including design and implementation.