Here’s a complete Product Requirements Document (PRD) for the deployment and environment configuration application based on the discussions and specifications provided.

---

# Product Requirements Document (PRD)

## Overview

This document outlines the requirements, workflows, entities, and APIs for a deployment and environment configuration application. The application enables users to manage their deployment environments, initiate deployments, and monitor the status of their applications.

## Key Concepts

- **Entity Management**: Core data models (entities) for managing users, environments, deployments, and their statuses.
- **Workflow Orchestration**: Workflows triggered by events from Cyoda, encapsulating the business logic required for different actions.
- **gRPC Communication**: For real-time notifications about workflow events and asynchronous processing.
- **RESTful API**: For user interactions and management of entities.

## Entities

1. **User**
   - **Description**: Represents application users who can authenticate and manage deployments.
   - **Fields**:
     - user_id: String
     - username: String
     - email: String
     - token: String

2. **Environment**
   - **Description**: Represents the deployment environment configuration for a user.
   - **Fields**:
     - environment_id: String
     - user_id: String
     - environment_name: String
     - config: Object (e.g., keyspace, namespace)

3. **Deployment**
   - **Description**: Represents an application deployment initiated by a user.
   - **Fields**:
     - deployment_id: String
     - environment_id: String
     - repository_url: String
     - is_public: Boolean
     - status: String
     - teamcity_build_id: String (reference to TeamCity)

4. **Deployment Cancellation**
   - **Description**: Represents a cancellation request for an ongoing or queued deployment.
   - **Fields**:
     - cancellation_id: String
     - deployment_id: String
     - comment: String
     - timestamp: String

## User Stories

1. As a user, I want to authenticate using a Bearer token so that I can securely access the system.
2. As a user, I want to create and configure my deployment environment, so I can manage my resources efficiently.
3. As a user, I want to initiate the deployment of my application via a specified repository, to ensure my application is up-to-date and accessible.
4. As a user, I want to check the status of my deployment, so I can monitor progress and resolve issues promptly.
5. As a user, I want to cancel my queued deployment if it's no longer needed, to avoid unnecessary resource allocation.

## API Endpoints

### User Entity APIs

**API Endpoint:** `POST /user/register`

**Description:**
- Registers a new user and generates a Bearer token for authentication.

**Pseudocode:**
```plaintext
# Receive user registration data
user = entity_service.add(User)
# Generate Bearer token for user
token = generate_token(user)
return { user_details: user, token: token }
```

### Environment Entity APIs

**API Endpoint:** `POST /deploy/cyoda-env`

**Description:**
- Creates a new environment configuration for the user.

**Pseudocode:**
```plaintext
# Receive environment data from the user
environment = entity_service.add(Environment)
# Trigger workflow for environment creation
trigger_environment_creation_workflow(environment)
return environment details to user
```

**API Endpoint:** `PUT /deploy/cyoda-env/{environment_id}`

**Description:**
- Updates the specified environment configuration.

**Pseudocode:**
```plaintext
# Receive updated environment data
environment = entity_service.update(Environment)
return environment details to user
```

### Deployment Entity APIs

**API Endpoint:** `POST /deploy/user_app`

**Description:**
- Initiates the deployment of the user's application through TeamCity.

**Pseudocode:**
```plaintext
# Receive deployment data from the user
deployment = entity_service.add(Deployment)
# Trigger build in TeamCity
teamcity_build_id = trigger_teamcity_build(deployment)
# Update deployment entity with TeamCity build ID
deployment.teamcity_build_id = teamcity_build_id
return deployment details to user
```

**API Endpoint:** `GET /deploy/user_app/status/{deployment_id}`

**Description:**
- Fetches the current status of the specified deployment.

**Pseudocode:**
```plaintext
# Fetch deployment details from Cyoda
deployment = entity_service.get(Deployment, deployment_id)
# Fetch current status from TeamCity
status = get_status_from_teamcity(deployment.teamcity_build_id)
return { deployment_id: deployment_id, status: status }
```

**API Endpoint:** `POST /deploy/cancel/user_app/{deployment_id}`

**Description:**
- Cancels a queued deployment.

**Pseudocode:**
```plaintext
# Receive cancellation request for the deployment
cancellation = entity_service.add(DeploymentCancellation)
# Trigger cancellation in TeamCity
cancel_teamcity_build(deployment.teamcity_build_id)
return { deployment_id: deployment_id, status: "cancellation requested" }
```

## Workflows and Processors

### User Entity Processors

**Processor: Save User**
```plaintext
function save_user(meta, user_data):
    # Validate user data
    if not is_valid_user(user_data):
        return error("Invalid user data")
    
    # Save user entity to Cyoda
    user = entity_service.add(User, user_data)
    
    # Generate Bearer token for the user
    token = generate_token(user)
    
    # Return user details along with the token
    return { user_details: user, token: token }
```

### Environment Entity Processors

**Processor: Save Environment**
```plaintext
function save_environment(meta, environment_data):
    # Validate environment configuration
    if not is_valid_environment(environment_data):
        return error("Invalid environment data")
    
    # Save environment entity to Cyoda
    environment = entity_service.add(Environment, environment_data)

    # Trigger workflow for environment creation
    trigger_environment_creation_workflow(environment)

    # Return environment details to the user
    return environment
```

**Processor: Update Environment**
```plaintext
function update_environment(meta, environment_id, environment_data):
    # Validate updated environment configuration
    if not is_valid_environment(environment_data):
        return error("Invalid environment update data")
    
    # Update environment entity in Cyoda
    environment = entity_service.update(Environment, environment_id, environment_data)

    # Return updated environment details to the user
    return environment
```

### Deployment Entity Processors

**Processor: Save Deployment**
```plaintext
function save_deployment(meta, deployment_data):
    # Validate deployment data
    if not is_valid_deployment(deployment_data):
        return error("Invalid deployment data")
    
    # Save deployment entity to Cyoda
    deployment = entity_service.add(Deployment, deployment_data)

    # Trigger build in TeamCity for the deployment
    teamcity_build_id = trigger_teamcity_build(deployment)

    # Update deployment entity with TeamCity build ID
    deployment.teamcity_build_id = teamcity_build_id
    
    # Return deployment details to the user
    return deployment
```

**Processor: Fetch Deployment Status**
```plaintext
function fetch_deployment_status(meta, deployment_id):
    # Fetch deployment details from Cyoda
    deployment = entity_service.get(Deployment, deployment_id)
    
    # Fetch current status from TeamCity
    status = get_status_from_teamcity(deployment.teamcity_build_id)

    # Return deployment status to the user
    return { deployment_id: deployment_id, status: status }
```

**Processor: Cancel Deployment**
```plaintext
function cancel_deployment(meta, deployment_id):
    # Fetch deployment details to be canceled
    deployment = entity_service.get(Deployment, deployment_id)

    if deployment.status != "queued":
        return error("Deployment is not in a cancellable state")
    
    # Trigger cancellation in TeamCity
    cancel_teamcity_build(deployment.teamcity_build_id)

    # Return confirmation of cancellation
    return { deployment_id: deployment_id, status: "cancellation requested" }
```

## Conclusion

This PRD serves as a comprehensive guide for the deployment and environment configuration application. It outlines the key concepts, user stories, APIs, workflows, and processors necessary for implementation. This document will assist the development team in building a robust application that meets user needs effectively.

--- 

Feel free to ask if you need any further modifications or additions!