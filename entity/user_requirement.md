### User Requirement Document

#### Title: Multi-User Deployment and Environment Configuration Management App

### User Stories

1. **User Story 1**: As a user, I want to authenticate via a token so that I can securely access the deployment functionalities of the application.
  
2. **User Story 2**: As a user, I want to initiate a deployment by providing the necessary configuration options, so that the application can deploy my environment.

3. **User Story 3**: As a user, I want to check the status of my deployments, so that I can monitor their progress and determine if any action is needed.

4. **User Story 4**: As a user, I want to retrieve the build statistics for my deployments, so that I can analyze the performance and success rates of my builds.

5. **User Story 5**: As a user, I want to cancel a queued deployment if necessary, so that I can manage my deployments efficiently.

---

### Journey Diagram

```mermaid
journey
    title User Journey for Deployment Management
    section Authentication
      User enters token: 5: User
      App validates token: 4: App
    section Deployment
      User initiates deployment: 5: User
      App triggers API to start deployment: 4: App
      App receives deployment confirmation: 4: App
    section Monitoring
      User requests status update: 5: User
      App fetches status: 4: App
      App returns current status: 4: App
    section Statistics
      User requests build statistics: 5: User
      App fetches statistics: 4: App
      App returns statistics: 4: App
    section Cancellation
      User requests to cancel deployment: 5: User
      App triggers cancellation API: 4: App
      App confirms cancellation: 4: App
```

---

### Sequence Diagram

```mermaid
sequenceDiagram
    participant U as User
    participant A as App
    participant C as Cyoda
    participant W as Workflow

    %% User Authentication Flow
    U->>A: Send Auth Request with Token
    A->>C: Validate Token
    C-->>A: Token Validated

    %% Initiate Deployment Flow
    U->>A: Request to Initiate Deployment
    A->>C: Trigger Deployment API
    C-->>A: Deployment Started Confirmation

    %% Monitor Deployment Status Flow
    U->>A: Request to Check Deployment Status
    A->>C: Fetch Current Status
    C-->>A: Return Current Status
    A-->>U: Display Deployment Status

    %% Fetch Build Statistics Flow
    U->>A: Request Build Statistics
    A->>C: Fetch Build Statistics
    C-->>A: Return Build Statistics
    A-->>U: Display Build Statistics

    %% Cancel Deployment Flow
    U->>A: Request to Cancel Deployment
    A->>C: Trigger Cancellation API
    C-->>A: Cancellation Confirmed
    A-->>U: Confirm Cancellation
```

---

### Explanation of Choices

1. **User Stories**: These stories capture the specific needs and functionalities that the users will interact with, ensuring that all key aspects of the application are addressed.

2. **Journey Diagram**: This diagram illustrates the steps a user will follow while interacting with the application, from authentication to initiating deployments and monitoring their status. It captures the flow of activities clearly.

3. **Sequence Diagram**: The sequence diagram details the interactions between the user, the application, and the Cyoda system, showing how requests and responses flow between them. This helps in visualizing how the components interact in real-time when actions are performed, ensuring clarity in understanding the process.

Overall, these diagrams and documents will serve as a comprehensive guide for the development and implementation of the application, aligning with Cyoda's architecture and ensuring that user needs are effectively met.