Based on the provided information, it looks like you're developing a deployment management application that interacts with a CI/CD system (TeamCity) to handle deployments of user applications and manage their statuses. To help you outline the entities for your application, I will summarize the key entities along with their properties and relationships. I will also provide a Mermaid ER diagram and class diagram to visualize the design.

### Entity Outline

1. **User**
   - **Properties**:
     - `user_id`: Unique identifier for the user (Primary Key)
     - `user_name`: Name of the user
     - `email`: Email address (optional)
     - `token`: Bearer authentication token (optional)
   
2. **Deployment**
   - **Properties**:
     - `deployment_id`: Unique identifier for the deployment (Primary Key)
     - `user_id`: Reference to the `User` entity (Foreign Key)
     - `repository_url`: URL of the repository being deployed
     - `is_public`: Boolean indicating if the deployment is public
     - `status`: Current status of the deployment (e.g., queued, running, completed, canceled)
     - `created_at`: Timestamp of when the deployment was created
     - `updated_at`: Timestamp of when the deployment was last updated
   
3. **Build**
   - **Properties**:
     - `build_id`: Unique identifier for the build (Primary Key)
     - `deployment_id`: Reference to the `Deployment` entity (Foreign Key)
     - `teamcity_id`: Identifier from TeamCity
     - `statistics`: JSON data containing build statistics (e.g., performance metrics)
     - `status`: Status of the build (e.g., running, success, failure)
     - `created_at`: Timestamp for when the build was initiated
     - `updated_at`: Timestamp for the last update of the build

### Entity Relationship Diagram (ERD)

Here's a Mermaid ER diagram to represent the relationships:

```mermaid
erDiagram
    User {
        string user_id PK "User Identifier"
        string user_name "Name of the user"
        string email "User's email address"
        string token "Bearer authentication token"
    }
    
    Deployment {
        string deployment_id PK "Deployment Identifier"
        string user_id FK "Reference to User"
        string repository_url "URL of the repository"
        boolean is_public "Public deployment flag"
        string status "Current status of deployment"
        datetime created_at "Timestamp of creation"
        datetime updated_at "Timestamp of last update"
    }
    
    Build {
        string build_id PK "Build Identifier"
        string deployment_id FK "Reference to Deployment"
        string teamcity_id "TeamCity Identifier"
        json statistics "Build statistics"
        string status "Current status of the build"
        datetime created_at "Timestamp of initiation"
        datetime updated_at "Timestamp of last update"
    }

    User ||--o{ Deployment : "has"
    Deployment ||--o{ Build : "initiates"
```

### Class Diagram

Below is a class diagram expressed in Mermaid syntax to highlight the structure of these entities and their properties:

```mermaid
classDiagram
    class User {
        +string user_id
        +string user_name
        +string email
        +string token
    }

    class Deployment {
        +string deployment_id
        +string user_id
        +string repository_url
        +boolean is_public
        +string status
        +datetime created_at
        +datetime updated_at
    }

    class Build {
        +string build_id
        +string deployment_id
        +string teamcity_id
        +json statistics
        +string status
        +datetime created_at
        +datetime updated_at
    }

    User "1" --o "0..*" Deployment : "has"
    Deployment "1" --o "0..*" Build : "initiates"
```

### Conclusion

This outline of entities and their properties, alongside the corresponding ER and class diagrams, provides a structured approach for modeling your deployment management application. You can further build on this design as new requirements arise or as you develop additional features in the application.