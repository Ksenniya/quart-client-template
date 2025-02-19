### Final Functional Requirements

#### User Authentication
1. **As a user, I want to authenticate using a Bearer token so that I can securely access the deployment features.**
   - **Endpoint**: `POST /auth/login`
     - **Request Format**:
       ```json
       {
           "username": "test",
           "password": "password"
       }
       ```
     - **Response Format**:
       ```json
       {
           "token": "Bearer <token>"
       }
       ```

#### Deployment Environments Management
2. **As a user, I want to create a deployment environment so that I can configure and manage my applications.**
   - **Endpoint**: `POST /environments`
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

3. **As a user, I want to check the status of my deployment environment so that I can monitor its progress.**
   - **Endpoint**: `GET /environments/{id}/status`
     - **Response Format**:
       ```json
       {
           "status": "in_progress",
           "details": "Build is currently being processed."
       }
       ```

4. **As a user, I want to retrieve statistics for my deployment environment so that I can analyze its performance.**
   - **Endpoint**: `GET /environments/{id}/statistics`
     - **Response Format**:
       ```json
       {
           "build_time": "10m",
           "success_rate": "90%"
       }
       ```

#### User Applications Management
5. **As a user, I want to deploy my application from a repository so that I can manage its deployment.**
   - **Endpoint**: `POST /user-apps`
     - **Request Format**:
       ```json
       {
           "repository_url": "http://....",
           "is_public": true
       }
       ```
     - **Response Format**:
       ```json
       {
           "build_id": "67890"
       }
       ```

6. **As a user, I want to check the status of my user application deployment so that I can monitor its progress.**
   - **Endpoint**: `GET /user-apps/{id}/status`
     - **Response Format**:
       ```json
       {
           "status": "completed",
           "details": "Build completed successfully."
       }
       ```

7. **As a user, I want to retrieve statistics for my user application deployment so that I can analyze its performance.**
   - **Endpoint**: `GET /user-apps/{id}/statistics`
     - **Response Format**:
       ```json
       {
           "build_time": "5m",
           "success_rate": "95%"
       }
       ```

8. **As a user, I want to cancel my user application deployment if necessary.**
   - **Endpoint**: `DELETE /user-apps/{id}`
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
           "message": "Build canceled successfully."
       }
       ```

### Summary
These functional requirements outline the actions that users can perform within the application, the corresponding API endpoints, and the expected request and response formats. This structure ensures clarity and provides a solid foundation for further development. If there are any additional requirements or modifications needed, please let me know!