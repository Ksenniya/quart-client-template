Here are the well-formatted final functional requirements for your project, presented in a clear and organized manner:

---

# Functional Requirements Document

## 1. User Authentication
- **As a user**, I want to authenticate using a Bearer token so that I can securely access the deployment features.

### API Endpoint
- `POST /auth`
  - **Request**:
    ```json
    {
        "username": "your_username",
        "password": "your_password"
    }
    ```
  - **Response**:
    ```json
    {
        "token": "your_bearer_token"
    }
    ```

---

## 2. Create Environment
- **As a user**, I want to create a deployment environment so that I can manage my application configurations.

### API Endpoint
- `POST /environments`
  - **Request**:
    ```json
    {
        "user_name": "test"
    }
    ```
  - **Response**:
    ```json
    {
        "build_id": "12345"
    }
    ```

---

## 3. Create User Application
- **As a user**, I want to create a user application deployment so that I can deploy my application.

### API Endpoint
- `POST /user-apps`
  - **Request**:
    ```json
    {
        "repository_url": "http://....",
        "is_public": true
    }
    ```
  - **Response**:
    ```json
    {
        "build_id": "67890"
    }
    ```

---

## 4. Get Environment Status
- **As a user**, I want to check the status of my deployment environment so that I can monitor its progress.

### API Endpoint
- `GET /environments/{id}/status`
  - **Response**:
    ```json
    {
        "status": "in-progress",
        "details": "Building..."
    }
    ```

---

## 5. Get Environment Statistics
- **As a user**, I want to retrieve statistics for my deployment environment to analyze its performance.

### API Endpoint
- `GET /environments/{id}/statistics`
  - **Response**:
    ```json
    {
        "build_time": "5m",
        "success_rate": "95%"
    }
    ```

---

## 6. Get User Application Status
- **As a user**, I want to check the status of my user application deployment.

### API Endpoint
- `GET /user-apps/{id}/status`
  - **Response**:
    ```json
    {
        "status": "completed",
        "details": "Deployment successful."
    }
    ```

---

## 7. Get User Application Statistics
- **As a user**, I want to retrieve statistics for my user application deployment.

### API Endpoint
- `GET /user-apps/{id}/statistics`
  - **Response**:
    ```json
    {
        "build_time": "3m",
        "success_rate": "90%"
    }
    ```

---

## 8. Cancel User Application
- **As a user**, I want to cancel a queued user application deployment if needed.

### API Endpoint
- `DELETE /user-apps/{id}`
  - **Request**:
    ```json
    {
        "comment": "Canceling a queued build",
        "readdIntoQueue": false
    }
    ```
  - **Response**:
    ```json
    {
        "message": "Build canceled successfully."
    }
    ```

---

This document outlines the functional requirements of your application in a structured format, detailing user stories, API endpoints, and request/response formats. Let me know if you need any further modifications or additional details!