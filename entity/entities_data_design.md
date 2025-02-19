Based on the provided JSON design document, here are the Mermaid diagrams for the entities and their relationships, as well as flowcharts for the workflows.

### Entity-Relationship Diagram (ERD)

```mermaid
erDiagram
    ENVIRONMENT {
        string user_name
    }

    USER_APP {
        string repository_url
        boolean is_public
    }

    STATUS {
        string status
        string repository_url
        boolean is_public
    }

    STATISTIC {
        string build_id
        json statistics
    }

    ENVIRONMENT ||--o{ USER_APP : has
    USER_APP ||--o{ STATUS : has
    USER_APP ||--o{ STATISTIC : has
```

### Class Diagram

```mermaid
classDiagram
    class Environment {
        +string user_name
    }

    class UserApp {
        +string repository_url
        +boolean is_public
    }

    class Status {
        +string status
        +string repository_url
        +boolean is_public
    }

    class Statistic {
        +string build_id
        +json statistics
    }

    Environment "1" -- "0..*" UserApp : contains
    UserApp "1" -- "0..*" Status : contains
    UserApp "1" -- "0..*" Statistic : contains
```

### Flowchart for Workflows

#### Workflow for User Application Creation

```mermaid
flowchart TD
    A[Start] --> B{Is User Logged In?}
    B -- Yes --> C[Create User App]
    B -- No --> D[Prompt User to Log In]
    D --> E[End]
    C --> F[Set Repository URL]
    F --> G[Set Public Status]
    G --> H[Save User App]
    H --> I[End]
```

#### Workflow for Status Update

```mermaid
flowchart TD
    A[Start] --> B{Is User App Exists?}
    B -- Yes --> C[Fetch User App]
    B -- No --> D[Show Error Message]
    D --> E[End]
    C --> F[Update Status]
    F --> G[Save Status]
    G --> H[End]
```

#### Workflow for Statistics Retrieval

```mermaid
flowchart TD
    A[Start] --> B{Is Build ID Valid?}
    B -- Yes --> C[Fetch Statistics]
    B -- No --> D[Show Error Message]
    D --> E[End]
    C --> F[Display Statistics]
    F --> G[End]
```

These diagrams and flowcharts represent the entities, their relationships, and workflows as specified in the JSON design document.