Based on the provided JSON design document, here are the Mermaid diagrams for the entities, class diagrams, and flow charts for workflows.

### Entity-Relationship Diagram (ERD)

```mermaid
erDiagram
    LOGIN {
        string username
        string password
    }
    
    ENVIRONMENT {
        string user_name
    }
    
    USER_APP {
        string repository_url
        boolean is_public
    }
    
    STATUS {
        string status
        string details
    }
    
    STATISTIC {
        string build_time
        string success_rate
    }
```

### Class Diagram

```mermaid
classDiagram
    class Login {
        +string username
        +string password
    }
    
    class Environment {
        +string user_name
    }
    
    class UserApp {
        +string repository_url
        +boolean is_public
    }
    
    class Status {
        +string status
        +string details
    }
    
    class Statistic {
        +string build_time
        +string success_rate
    }
```

### Flow Chart for Workflows

Assuming a generic workflow for logging in and checking the status of a user application, here’s a flowchart:

```mermaid
flowchart TD
    A[Start] --> B[User enters username and password]
    B --> C{Is login successful?}
    C -- Yes --> D[Load user environment]
    C -- No --> E[Display error message]
    D --> F[User selects application]
    F --> G[Check application status]
    G --> H{Is application in progress?}
    H -- Yes --> I[Display status details]
    H -- No --> J[Display completed status]
    I --> K[End]
    J --> K
    E --> K
```

These diagrams represent the entities, their relationships, and a basic workflow based on the provided JSON design document. If you have specific workflows in mind, please provide more details, and I can adjust the flowchart accordingly.