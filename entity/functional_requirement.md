```markdown
# Functional Requirements Document

## API Endpoints

### 1. GET /hello
- **Description**: Retrieves a personalized greeting message.
- **Request Format**: 
  - Method: GET
  - Query Parameter: `name` (string) - The name of the person to greet.
- **Response Format**: 
  - Content-Type: application/json
  - Example Request: 
    ```
    GET /hello?name=John
    ```
  - Example Response:
    ```json
    {
        "message": "Hello, John!"
    }
    ```

### 2. POST /calculate
- **Description**: Performs a calculation based on provided input and retrieves external data if necessary.
- **Request Format**: 
  - Method: POST
  - Content-Type: application/json
  - Example Request:
    ```json
    {
        "operation": "add",
        "numbers": [1, 2]
    }
    ```
- **Response Format**: 
  - Content-Type: application/json
  - Example Response:
    ```json
    {
        "result": 3
    }
    ```

### 3. POST /data
- **Description**: Fetches data from an external source and processes it.
- **Request Format**: 
  - Method: POST
  - Content-Type: application/json
  - Example Request:
    ```json
    {
        "query": "SELECT * FROM users"
    }
    ```
- **Response Format**: 
  - Content-Type: application/json
  - Example Response:
    ```json
    {
        "data": [
            {
                "id": 1,
                "name": "John Doe"
            },
            {
                "id": 2,
                "name": "Jane Doe"
            }
        ]
    }
    ```

## User-App Interaction Diagram

```mermaid
sequenceDiagram
    participant User
    participant App

    User->>App: GET /hello?name=John
    App-->>User: Respond with greeting message

    User->>App: POST /calculate
    App-->>User: Respond with calculation result

    User->>App: POST /data
    App-->>User: Respond with external data
```

```mermaid
journey
    title User Journey in the Application
    section Greeting
      User requests personalized greeting: 5: User
      App responds with personalized greeting message: 5: App
    section Calculation
      User requests calculation: 4: User
      App processes request: 4: App
      App responds with calculation result: 5: App
    section Data Retrieval
      User requests external data: 3: User
      App processes request: 4: App
      App responds with external data: 5: App
```
```