Based on the provided JSON design document, here are the Mermaid diagrams for the entities and workflows.

### Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    AUTH {
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
        string details
    }

    STATISTIC {
        object statistics
    }

    AUTH ||--o{ ENVIRONMENT : "authenticates"
    ENVIRONMENT ||--o{ USER_APP : "uses"
    USER_APP ||--o{ STATUS : "has"
    USER_APP ||--o{ STATISTIC : "generates"
```

### Class Diagram

```mermaid
classDiagram
    class Auth {
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
        +string details
    }

    class Statistic {
        +object statistics
    }

    Auth <|-- Environment
    Environment <|-- UserApp
    UserApp <|-- Status
    UserApp <|-- Statistic
```

### Flow Chart for Workflows

#### Workflow for User Authentication

```mermaid
flowchart TD
    A[Start] --> B[User submits credentials]
    B --> C{Credentials valid?}
    C -- Yes --> D[Generate token]
    C -- No --> E[Return error]
    D --> F[Return token]
    E --> F
    F --> G[End]
```

#### Workflow for Environment Setup

```mermaid
flowchart TD
    A[Start] --> B[User initiates environment setup]
    B --> C[Check build ID]
    C --> D{Build ID exists?}
    D -- Yes --> E[Update environment status]
    D -- No --> F[Create new environment]
    E --> G[Return environment details]
    F --> G
    G --> H[End]
```

#### Workflow for User Application Management

```mermaid
flowchart TD
    A[Start] --> B[User submits app details]
    B --> C[Validate app details]
    C --> D{Details valid?}
    D -- Yes --> E[Store app information]
    D -- No --> F[Return error]
    E --> G[Return app status]
    F --> G
    G --> H[End]
```

#### Workflow for Status Update

```mermaid
flowchart TD
    A[Start] --> B[Receive status update]
    B --> C[Validate status]
    C --> D{Status valid?}
    D -- Yes --> E[Update status record]
    D -- No --> F[Return error]
    E --> G[Return updated status]
    F --> G
    G --> H[End]
```

#### Workflow for Statistics Generation

```mermaid
flowchart TD
    A[Start] --> B[Collect statistics data]
    B --> C[Calculate statistics]
    C --> D[Store statistics]
    D --> E[Return statistics]
    E --> F[End]
```

These diagrams represent the entities, their relationships, and workflows as specified in the JSON design document.