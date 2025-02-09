Got it! Here’s the updated Markdown representation of the Cyoda design JSON, excluding the User entity:

---

# Cyoda Application Design

## Entities Overview

### 1. Deployment Environment Entity
- **Description**: Represents the deployment environment that is being managed and built.
- **Workflow**: Deployment Request Workflow

#### Deployment Environment Entity JSON Example
```json
{
    "env_id": "env_456",
    "deployment_config": {
        "repository_url": "http://example.com/repo.git",
        "is_public": true
    },
    "build_id": "build_789"
}
```

#### Deployment Request Workflow Flowchart
```mermaid
flowchart TD
    A[Start Deployment Request] -->|transition: submit_deployment_request, processor: submit_deployment_process| B[Deployment Request Submitted]
    B -->|transition: trigger_build, processor: trigger_build_process| C[Build Triggered]
    C --> D[End Deployment Process]
```

---

### 2. User Application Entity
- **Description**: Represents the user's application that needs to be deployed.
- **Workflow**: User Application Deployment Workflow

#### User Application Entity JSON Example
```json
{
    "app_id": "app_101",
    "repository_url": "http://example.com/repo.git",
    "is_public": true,
    "env_id": "env_456"
}
```

#### User Application Deployment Workflow Flowchart
```mermaid
flowchart TD
    A[Start User Application Deployment] -->|transition: submit_user_app_deployment, processor: submit_user_app_process| B[User Application Deployment Submitted]
    B -->|transition: trigger_build, processor: trigger_user_app_build_process| C[Build Triggered]
    C --> D[End User Application Deployment Process]
```

---

### 3. Build Entity
- **Description**: Represents the build process and status for both deployment environments and user applications.
- **Workflow**: Build Workflow

#### Build Entity JSON Example
```json
{
    "build_id": "build_789",
    "env_id": "env_456",
    "app_id": "app_101",
    "status": "successful",
    "build_time": "5min",
    "success_rate": "95%"
}
```

#### Build Workflow Flowchart
```mermaid
flowchart TD
    A[Start Build Process] -->|transition: start_build, processor: start_build_process| B[Build In Progress]
    B -->|transition: update_status, processor: update_build_status_process| C[Build Completed]
    C --> D[End Build Process]
```

---

## Summary

This document outlines the core entities within the Cyoda application design, highlighting their purpose and the associated workflows. Each entity includes a JSON example to illustrate its structure and a flowchart depicting the workflow processes to clarify how the various components interact in the system.

If you need further modifications or have any other questions, feel free to ask!