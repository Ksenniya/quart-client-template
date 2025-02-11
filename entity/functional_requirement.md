Here are the final functional requirements for your application, presented in a clear and organized format:

### Functional Requirements

#### 1. User Deployment of Environment
- **User Story**: As a user, I want to deploy a Cyoda environment so that I can manage my deployment configurations.
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

#### 2. User Deployment of User App
- **User Story**: As a user, I want to deploy a user application so that I can manage my application configurations.
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

#### 3. Check Status of Cyoda Environment Deployment
- **User Story**: As a user, I want to check the status of my Cyoda environment deployment to see if it succeeded or failed.
- **API Endpoint**: `GET /deploy/cyoda-env/status/{id}`
  - **Response Format**:
    ```json
    {
      "status": "success",
      "details": "Deployment completed successfully."
    }
    ```

#### 4. Get Statistics for Cyoda Environment Deployment
- **User Story**: As a user, I want to retrieve statistics for my Cyoda environment deployment to analyze its performance.
- **API Endpoint**: `GET /deploy/cyoda-env/statistics/{id}`
  - **Response Format**:
    ```json
    {
      "build_id": "12345",
      "duration": "5m",
      "success_rate": "100%"
    }
    ```

#### 5. Check Status of User App Deployment
- **User Story**: As a user, I want to check the status of my user app deployment to see if it succeeded or failed.
- **API Endpoint**: `GET /deploy/user_app/status/{id}`
  - **Response Format**:
    ```json
    {
      "status": "failed",
      "details": "Deployment encountered an error."
    }
    ```

#### 6. Get Statistics for User App Deployment
- **User Story**: As a user, I want to retrieve statistics for my user app deployment to analyze its performance.
- **API Endpoint**: `GET /deploy/user_app/statistics/{id}`
  - **Response Format**:
    ```json
    {
      "build_id": "67890",
      "duration": "3m",
      "success_rate": "90%"
    }
    ```

### Additional Considerations
- **Error Handling**: Standardized error messages and codes should be implemented in the API responses.
- **Data Validation**: Input data should be validated for required fields and correct formats.
- **Documentation**: API documentation should be created for user reference.

This structure provides a comprehensive overview of the functional requirements for your application.