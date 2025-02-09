Absolutely! Migrating your application to Cyoda Cloud is a great step towards enhancing its scalability, reliability, and performance. Let’s outline the entities involved in your application along with a brief explanation of each entity's role. I’ll provide Mermaid diagrams to visualize the sequences involved in the API interactions based on your functional requirements.

### Entities Overview

1. **User**: The entity representing the person interacting with the application. Users can deploy environments and manage application deployments.
  
2. **API**: The interface through which users interact with the application. It handles requests and communicates with the TeamCity service.

3. **TeamCity**: An external service used for managing builds and deployment pipelines. The API interacts with TeamCity to queue builds, check statuses, and cancel builds.

### Mermaid Diagrams

#### 1. Manage Environment Deployment

```mermaid
sequenceDiagram
    participant User
    participant API
    participant TeamCity
    
    User->>API: POST /deploy/cyoda-env { user_name: "test" }
    API->>TeamCity: POST Build Queue (KubernetesPipeline_CyodaSaas)
    TeamCity-->>API: return build ID
    API-->>User: { build_id: "12345" }
```

#### 2. Deploy User Application

```mermaid
sequenceDiagram
    participant User
    participant API
    participant TeamCity
    
    User->>API: POST /deploy/user_app { repository_url: "http://....", is_public: true }
    API->>TeamCity: POST Build Queue (KubernetesPipeline_CyodaSaasUserEnv)
    TeamCity-->>API: return build ID
    API-->>User: { build_id: "67890" }
```

#### 3. Get Deployment Status

```mermaid
sequenceDiagram
    participant User
    participant API
    participant TeamCity
    
    User->>API: GET /deploy/cyoda-env/status/12345
    API->>TeamCity: GET Build Queue Status
    TeamCity-->>API: return build status
    API-->>User: { status: "Running" }
```

#### 4. Cancel User Application Build

```mermaid
sequenceDiagram
    participant User
    participant API
    participant TeamCity
    
    User->>API: POST /deploy/cancel/user_app/67890 { comment: "Canceling a queued build", readdIntoQueue: false }
    API->>TeamCity: Cancel Build Request
    TeamCity-->>API: Build canceled
    API-->>User: No content
```

### Functional Requirements Summary

1. **Deploy Environment**
   - **Endpoint**: `POST /deploy/cyoda-env`
   - **Request**: `{ "user_name": "test" }`
   - **Response Success**: `{ "build_id": "12345" }`

2. **Deploy User Application**
   - **Endpoint**: `POST /deploy/user_app`
   - **Request**: `{ "repository_url": "http://....", "is_public": "true" }`
   - **Response Success**: `{ "build_id": "67890" }`

3. **Get Deployment Status**
   - **Endpoint**: `GET /deploy/cyoda-env/status/{id}`
   - **Response Success**: `{ "status": "Running", "repository_url": "http://....", "is_public": "true" }`

4. **Cancel User Application Build**
   - **Endpoint**: `POST /deploy/cancel/user_app/{id}`
   - **Request**: `{ "comment": "Canceling a queued build", "readdIntoQueue": false }`
   - **Response**: No content on success.

These diagrams and outlines should give you a clear picture of how the application flows and the entities involved. If you have any more specific entities or require further details or adjustments, feel free to ask!