### User Requirement Document

This user requirement document outlines user stories, a journey diagram, and a sequence diagram customized for the deployment and environment configuration application.

#### User Stories
1. **As a user**, I want to authenticate using a Bearer token so that I can securely access the system.
2. **As a user**, I want to create and configure my deployment environment, so I can manage my resources efficiently.
3. **As a user**, I want to initiate the deployment of my application via a specified repository, to ensure my application is up-to-date and accessible.
4. **As a user**, I want to check the status of my deployment, so I can monitor progress and resolve issues promptly.
5. **As a user**, I want to cancel my queued deployment if it's no longer needed, to avoid unnecessary resource allocation.
6. **As a user**, I want to view the statistics of my deployed application to understand its performance and resource usage.

### Journey Diagram

```mermaid
journey
    title User Journey for Deployment and Environment Configuration
    section User Authentication
      User logs in to obtain Bearer token: 5: User
      Application validates credentials: 3: App

    section Environment Configuration
      User sends request to create environment: 5: User
      Application processes the request: 3: App
      Application saves entity to Cyoda: 3: App
      Cyoda confirms entity save: 3: Cyoda
      Cyoda triggers workflow event: 3: Cyoda
      App receives workflow start notification: 3: App
      App executes environment configuration workflow: 3: Workflow

    section Application Deployment
      User sends request to deploy application: 5: User
      Application processes the request: 3: App
      Application saves deployment to Cyoda: 3: App
      Cyoda triggers deployment workflow: 3: Cyoda
      App receives workflow start notification: 3: App
      App executes deployment workflow processors: 3: Workflow

    section Status Check
      User requests status of deployment: 5: User
      Application fetches status from Cyoda: 3: App
      Cyoda returns deployment status: 3: Cyoda
      Application returns status to user: 5: User

    section Cancel Deployment
      User requests to cancel deployment: 5: User
      Application processes cancellation request: 3: App
      Cyoda confirms cancellation: 3: Cyoda
      Application informs user of cancellation: 5: User
```

### Sequence Diagram

```mermaid
sequenceDiagram
    participant U as User
    participant A as App
    participant C as Cyoda
    participant W as Workflow (Business Logic)
    participant G as gRPC Server

    %% User Authentication Flow
    U->>A: Log in (request Bearer token)
    A-->>U: Return Bearer token

    %% Create Environment Flow
    U->>A: Request to create environment
    A->>C: Save environment to Cyoda
    C-->>A: Confirmation of environment save
    C->>G: Trigger workflow event for environment creation
    G-->>A: Notify App to start workflow
    A->>W: Execute environment configuration workflow
    W-->>A: Workflow completed

    %% Deploy Application Flow
    U->>A: Request to deploy application
    A->>C: Save deployment to Cyoda
    C-->>A: Confirmation of deployment save
    C->>G: Trigger deployment workflow
    G-->>A: Notify App to start deployment workflow
    A->>W: Execute deployment workflow
    W-->>A: Deployment workflow completed

    %% Status Check Flow
    U->>A: Request deployment status
    A->>C: Fetch deployment status
    C-->>A: Return deployment status
    A-->>U: Return deployment status

    %% Cancel Deployment Flow
    U->>A: Request to cancel deployment
    A->>C: Cancel deployment in Cyoda
    C-->>A: Confirmation of cancellation
    A-->>U: Inform user of cancellation
```

### Explanation of Choices
- **User Stories**: I structured the user stories to cover all necessary interactions a user may need to perform. Each story focuses on a specific user requirement that adds value to the user experience.
  
- **Journey Diagram**: The journey diagram reflects the flow from user authentication to environment configuration and application deployment, including status checks and cancellation requests. This provides a visual representation of end-user interactions.

- **Sequence Diagram**: The sequence diagram details the interactions between the user, application, Cyoda, and workflows. I used this format to show the asynchronous nature of requests and how workflows are triggered and processed, making it easier to visualize the system's operation, especially in a Cyoda-like application architecture.

All diagrams are tailored to fit the specific context and requirements of the deployment and environment configuration app, ensuring clarity and usability for stakeholders involved in the development process.