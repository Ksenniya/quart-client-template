```markdown
# Functional Requirements for Hello World App

## API Endpoints

### 1. GET /hello
- **Description**: Retrieve a simple greeting message.
- **Request Format**: 
  - Method: GET
  - URL: `/hello`
  
- **Response Format**:
  - Status Code: 200 OK
  - Body: 
    ```json
    {
      "message": "Hello, World!"
    }
    ```

### 2. POST /greet
- **Description**: Accept a name and return a personalized greeting message.
- **Request Format**:
  - Method: POST
  - URL: `/greet`
  - Body:
    ```json
    {
      "name": "string"
    }
    ```

- **Response Format**:
  - Status Code: 200 OK
  - Body:
    ```json
    {
      "message": "Hello, {name}!"
    }
    ```

## User-App Interaction Diagram

```mermaid
sequenceDiagram
    participant User
    participant App

    User->>App: Sends GET /hello
    App-->>User: Returns greeting message

    User->>App: Sends POST /greet with name
    App-->>User: Returns personalized greeting message
```

## Journey Diagram

```mermaid
journey
    title User Journey for Hello World App
    section Greeting Retrieval
      User initiates GET request: 5: User
      App responds with greeting: 5: App
    section Personalized Greeting
      User sends POST request with name: 5: User
      App responds with personalized message: 5: App
``` 
```