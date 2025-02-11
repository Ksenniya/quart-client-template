Here are the final functional requirements for your project, formatted clearly for easy reference:

### Functional Requirements

#### User Stories

1. **User Story: Deploy Cyoda Environment**
   - **As a** user, **I want** to deploy a Cyoda environment **so that** I can manage my application environment.
   - **API Endpoint**: `POST /deploy/cyoda-env`
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

2. **User Story: Deploy User Application**
   - **As a** user, **I want** to deploy my application **so that** I can make it accessible.
   - **API Endpoint**: `POST /deploy/user_app`
     - **Request**:
       ```json
       {
         "repository_url": "http://....",
         "is_public": "true"
       }
       ```
     - **Response**:
       ```json
       {
         "build_id": "67890"
       }
       ```

3. **User Story: Check Deployment Status**
   - **As a** user, **I want** to check the status of my deployment **so that** I can monitor its progress.
   - **API Endpoint**: `GET /deploy/cyoda-env/status/{id}`
     - **Response**:
       ```json
       {
         "status": "running",
         "details": "Deployment is in progress."
       }
       ```

4. **User Story: Retrieve Deployment Statistics**
   - **As a** user, **I want** to retrieve statistics for my deployment **so that** I can analyze its performance.
   - **API Endpoint**: `GET /deploy/cyoda-env/statistics/{id}`
     - **Response**:
       ```json
       {
         "statistics": {
           "duration": "5m",
           "success_rate": "100%"
         }
       }
       ```

#### Use Cases

1. **Use Case: Deploy Cyoda Environment**
   - **Actors**: User
   - **Preconditions**: User has a valid Bearer token.
   - **Main Flow**:
     1. User sends a request to `POST /deploy/cyoda-env` with the user name.
     2. System processes the request and interacts with TeamCity.
     3. System returns the build ID.

2. **Use Case: Deploy User Application**
   - **Actors**: User
   - **Preconditions**: User has a valid Bearer token.
   - **Main Flow**:
     1. User sends a request to `POST /deploy/user_app` with repository details.
     2. System processes the request and interacts with TeamCity.
     3. System returns the build ID.

3. **Use Case: Check Deployment Status**
   - **Actors**: User
   - **Preconditions**: User has a valid Bearer token.
   - **Main Flow**:
     1. User sends a request to `GET /deploy/cyoda-env/status/{id}`.
     2. System retrieves the status from TeamCity.
     3. System returns the deployment status.

4. **Use Case: Retrieve Deployment Statistics**
