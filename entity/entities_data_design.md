Based on the provided JSON design document, here are the Mermaid diagrams for the entities and workflows.

### Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    TOKEN {
        string token
    }

    ENVIRONMENT {
        string user_name
        string build_id
        string status
    }

    USER_APP {
        string repository_url
        boolean is_public
        string build_id
        string status
    }

    STATUS {
        string status
        string build_id
    }

    STATISTIC {
        string build_id
        string duration
        boolean success
    }

    TOKEN ||--o{ ENVIRONMENT : has
    ENVIRONMENT ||--o{ USER_APP : has
    USER_APP ||--o{ STATUS : has
    USER_APP ||--o{ STATISTIC : has
```

### Class Diagram

```mermaid
classDiagram
    class Token {
        +string token
    }

    class Environment {
        +string user_name
        +string build_id
        +string status
    }

    class UserApp {
        +string repository_url
        +boolean is_public
        +string build_id
        +string status
    }

    class Status {
        +string status
        +string build_id
    }

    class Statistic {
        +string build_id
        +string duration
        +boolean success
    }

    Token --> Environment
    Environment --> UserApp
    UserApp --> Status
    UserApp --> Statistic
```

### Flow Chart for Workflows

#### Workflow for Building an Application

```mermaid
flowchart TD
    A[Start] --> B[Receive User Request]
    B --> C[Validate Token]
    C -->|Valid| D[Fetch Environment Details]
    C -->|Invalid| E[Return Error]
    D --> F[Queue Build in User App]
    F --> G[Update Status to Running]
    G --> H[Run Build Process]
    H --> I{Is Build Successful?}
    I -->|Yes| J[Update Status to Success]
    I -->|No| K[Update Status to Failure]
    J --> L[Record Statistics]
    K --> L
    L --> M[Return Build Results]
    M --> N[End]
```

These diagrams represent the entities and their relationships, as well as the workflow for building an application based on the provided JSON design document.