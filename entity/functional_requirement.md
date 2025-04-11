```markdown
# Functional Requirements Document

## API Endpoints

### 1. User Registration
- **Endpoint**: `POST /api/register`
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
    "message": "User registered successfully.",
    "userId": "string"
  }
  ```

### 2. User Login
- **Endpoint**: `POST /api/login`
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
    "message": "Login successful.",
    "token": "string"
  }
  ```

### 3. Retrieve User Profile
- **Endpoint**: `GET /api/user/profile`
- **Request Format**: (Authorization required via Bearer token)
  - Headers: `Authorization: Bearer <token>`
- **Response Format**:
  ```json
  {
    "userId": "string",
    "username": "string",
    "email": "string"
  }
  ```

### 4. Update User Profile
- **Endpoint**: `POST /api/user/profile`
- **Request Format**:
  ```json
  {
    "username": "string",
    "email": "string"
  }
  ```
- **Response Format**:
  ```json
  {
    "message": "Profile updated successfully."
  }
  ```

### 5. Data Retrieval
- **Endpoint**: `POST /api/data/retrieve`
- **Request Format**:
  ```json
  {
    "query": "string"
  }
  ```
- **Response Format**:
  ```json
  {
    "data": [
      {
        "id": "string",
        "value": "string"
      }
    ]
  }
  ```

## User-App Interaction Diagram

```mermaid
sequenceDiagram
    participant User
    participant App
    User->>App: Register (POST /api/register)
    App-->>User: User registered (response)
    User->>App: Login (POST /api/login)
    App-->>User: Login successful (response)
    User->>App: Request Profile (GET /api/user/profile)
    App-->>User: User Profile (response)
    User->>App: Update Profile (POST /api/user/profile)
    App-->>User: Profile updated (response)
    User->>App: Retrieve Data (POST /api/data/retrieve)
    App-->>User: Data retrieved (response)
```

## User Journey Diagram

```mermaid
journey
    title User Journey for Registration and Profile Management
    section Registration
      User enters details: 5: User
      User submits registration: 5: User
      App confirms registration: 5: App
    section Login
      User enters credentials: 5: User
      User submits login: 5: User
      App confirms login: 5: App
    section Profile Management
      User requests profile: 5: User
      App sends profile data: 5: App
      User updates profile: 5: User
      App confirms profile update: 5: App
    section Data Retrieval
      User requests data: 5: User
      App retrieves and sends data: 5: App
```
```