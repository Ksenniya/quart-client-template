```markdown
# Functional Requirements for Hello World Application

## API Endpoints

### 1. GET /hello
- **Description**: Retrieves a simple "Hello, World!" message.
- **Request Format**: 
  - No parameters required.
- **Response Format**: 
  - **200 OK**
    ```json
    {
      "message": "Hello, World!"
    }
    ```

### 2. POST /greet
- **Description**: Accepts a name and returns a personalized greeting message.
- **Request Format**:
  - **Body**:
    ```json
    {
      "name": "string"
    }
    ```
- **Response Format**: 
  - **200 OK**
    ```json
    {
      "message": "Hello, {name}!"
    }
    ```
  - **400 Bad Request** (if name is missing)
    ```json
    {
      "error": "Name is required."
    }
    ```

## User-App Interaction

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend

    User->>Frontend: Access application
    Frontend->>Backend: GET /hello
    Backend-->>Frontend: 200 OK { "message": "Hello, World!" }
    Frontend-->>User: Display message

    User->>Frontend: Submit name
    Frontend->>Backend: POST /greet { "name": "Alice" }
    Backend-->>Frontend: 200 OK { "message": "Hello, Alice!" }
    Frontend-->>User: Display personalized message
```
```