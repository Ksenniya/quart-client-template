Here’s a well-formatted list of final functional requirements presented as user stories along with the corresponding API endpoints:

---

### **Functional Requirements**

#### **1. User Authentication**
- **User Story:** As a user, I want to authenticate using a Bearer token so that I can securely access the deployment services.
  - **API Endpoint:**
    - `POST /auth`
      - **Request:** 
        ```json
        {
          "token": "Bearer <token>"
        }
        ```
      - **Response:** 
        ```json
        {
          "status": "authenticated"
        }
        ```

#### **2. Manage Environment Configuration**
- **User Story:** As a user, I want to create a new environment configuration so that I can manage deployments for my applications.
  - **API Endpoint:**
    - `POST /environments`
      - **Request:** 
        ```json
        {
          "user_name": "test"
        }
        ```
      - **Response:** 
        ```json
        {
          "build_id": "<id>"
        }
        ```

- **User Story:** As a user, I want to check the status of my environment deployment to see if it is successful or failed.
  - **API Endpoint:**
    - `GET /environments/{id}/status`
      - **Response:** 
        ```json
        {
          "status": "success|failed",
          "details": "..."
        }
        ```

- **User Story:** As a user, I want to retrieve statistics about my environment deployment to analyze performance.
  - **API Endpoint:**
    - `GET /environments/{id}/statistics`
      - **Response:** 
        ```json
        {
          "statistics": {
            "duration": "10s",
            "success_rate": "100%"
          }
        }
        ```

#### **3. Manage User Applications**
- **User Story:** As a user, I want to deploy my application by providing a repository URL and visibility settings so that I can manage my application deployments.
  - **API Endpoint:**
    - `POST /user-apps`
      - **Request:** 
        ```json
        {
          "repository_url": "http://....",
          "is_public": true
        }
        ```
      - **Response:** 
        ```json
        {
          "build_id": "<id>"
        }
        ```

- **User Story:** As a user, I want to check the status of my application deployment to see if it is successful or failed.
  - **API Endpoint:**
    - `GET /user-apps/{id}/status`
      - **Response:** 
        ```json
        {
          "status": "success|failed",
          "details": "..."
        }
        ```

- **User Story:** As a user, I want to retrieve statistics about my application deployment to analyze performance.
  - **API Endpoint:**
    - `GET /user-apps/{id}/statistics`
      - **Response:** 
        ```json
        {
          "statistics": {
            "duration": "10s",
            "success_rate": "100%"
          }
        }
        ```

- **User Story:** As a user, I want to cancel my application deployment if it is queued.
  - **API Endpoint:**
    - `POST /user-apps/{id}/cancel`
      - **Request:** 
        ```json
        {
          "comment": "Canceling a queued build"
        }
        ```
      - **Response:** 
        ```json
        {
          "status": "canceled"
        }
        ```

---

This structured format outlines the complete functional requirements for your project, making it easy to understand and implement. If you need any changes or further details, feel free to ask!