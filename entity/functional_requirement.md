```markdown
# Functional Requirements Document

## API Endpoints

### 1. User Registration
- **Endpoint**: `/api/register`
- **Method**: POST
- **Request Format**: 
  ```json
  {
    "username": "string",
    "password": "string",
    "email": "string"
  }
  ```
- **Response Format**: 
  ```json
  {
    "message": "User registered successfully",
    "userId": "string"
  }
  ```

### 2. User Login
- **Endpoint**: `/api/login`
- **Method**: POST
- **Request Format**: 
  ```json
  {
    "username": "string",
    "password": "string"
  }
  ```
- **Response Format**: 
  ```json
  {
    "message": "Login successful",
    "token": "string"
  }
  ```

### 3. Retrieve User Data
- **Endpoint**: `/api/user`
- **Method**: GET
- **Request Format**: 
  - Headers: 
    ```json
    {
      "Authorization": "Bearer token"
    }
    ```
- **Response Format**: 
  ```json
  {
    "username": "string",
    "email": "string",
    "createdAt": "date"
  }
  ```

### 4. External Data Retrieval
- **Endpoint**: `/api/external-data`
- **Method**: POST
- **Request Format**: 
  ```json
  {
    "query": "string"
  }
  ```
- **Response Format**: 
  ```json
  {
    "data": "array of objects"
  }
  ```

## User-App Interaction

```mermaid
sequenceDiagram
    participant User
    participant App
    User->>App: Register
    App-->>User: User registered successfully
    User->>App: Login
    App-->>User: Login successful
    User->>App: Retrieve User Data
    App-->>User: User data returned
    User->>App: Request External Data
    App-->>User: External data returned
```
```