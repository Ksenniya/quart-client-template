Based on the provided JSON design document, here are the requested Mermaid diagrams for the entities and workflows.

### Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    USER {
        string username
        string password
        string token
    }
    ENVIRONMENT {
        string id
        string user_name
        string env_config
        string build_id
    }
    DEPLOYMENT {
        string id
        string repository_url
        boolean is_public
        string build_id
    }
    STATUS {
        string id
        string status
        string repository_url
        boolean is_public
    }
    STATISTICS {
        string id
        object statistics
    }
    CANCELLATION {
        string id
        string comment
        boolean readdIntoQueue
        string message
    }

    USER ||--o{ ENVIRONMENT : creates
    USER ||--o{ DEPLOYMENT : initiates
    ENVIRONMENT ||--o{ STATUS : has
    ENVIRONMENT ||--o{ STATISTICS : has
    DEPLOYMENT ||--o{ CANCELLATION : can_cancel
```

### Class Diagram

```mermaid
classDiagram
    class User {
        +string username
        +string password
        +string token
        +login()
    }

    class Environment {
        +string id
        +string user_name
        +string env_config
        +string build_id
        +create()
        +getStatus()
        +getStatistics()
    }

    class Deployment {
        +string id
        +string repository_url
        +boolean is_public
        +string build_id
        +deploy()
        +cancel()
    }

    class Status {
        +string id
        +string status
        +string repository_url
        +boolean is_public
    }

    class Statistics {
        +string id
        +object statistics
    }

    class Cancellation {
        +string id
        +string comment
        +boolean readdIntoQueue
        +cancel()
    }

    User --> Environment : creates
    User --> Deployment : initiates
    Environment --> Status : has
    Environment --> Statistics : has
    Deployment --> Cancellation : can_cancel
```

### Flow Chart for Each Workflow

#### User Authentication Workflow

```mermaid
flowchart TD
    A[User] -->|POST /auth/login| B[API]
    B -->|Returns token| C[User]
```

#### Create Environment Workflow

```mermaid
flowchart TD
    A[User] -->|POST /environments| B[API]
    B -->|Mock API call to create environment| C[TeamCity]
    C -->|Returns build_id| B
    B -->|Returns build_id| A
```

#### Deploy Application Workflow

```mermaid
flowchart TD
    A[User] -->|POST /deployments| B[API]
    B -->|Mock API call to deploy application| C[TeamCity]
    C -->|Returns build_id| B
    B -->|Returns deployment message| A
```

#### Get Environment Status Workflow

```mermaid
flowchart TD
    A[User] -->|GET /environments/{id}/status| B[API]
    B -->|Mock API call to get status| C[TeamCity]
    C -->|Returns status| B
    B -->|Returns status| A
```

#### Get Environment Statistics Workflow

```mermaid
flowchart TD
    A[User] -->|GET /environments/{id}/statistics| B[API]
    B -->|Mock API call to get statistics| C[TeamCity]
    C -->|Returns statistics| B
    B -->|Returns statistics| A
```

#### Cancel Deployment Workflow

```mermaid
flowchart TD
    A[User] -->|POST /deployments/{id}/cancel| B[API]
    B -->|Mock API call to cancel deployment| C[TeamCity]
    C -->|Returns cancellation confirmation| B
    B -->|Returns cancellation message| A
```

These diagrams represent the entities, their relationships, and the workflows as specified in the provided JSON design document.