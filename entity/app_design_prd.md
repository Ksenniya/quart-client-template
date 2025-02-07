Below is a textual representation of the Cyoda design JSON outlining the entities and their corresponding workflows, along with flowcharts for each workflow. 

### Cyoda Design JSON Representation

```json
{
  "can_proceed": false,
  "entities": [
    {
      "entity_name": "cyoda_env",
      "entity_source": "ENTITY_EVENT",
      "entity_type": "DEPLOYMENT_ENVIRONMENT",
      "entity_workflow": {
        "name": "cyoda_env_workflow",
        "class_name": "com.cyoda.tdb.model.treenode.TreeNodeEntity",
        "transitions": [
          {
            "name": "start_deployment",
            "description": "Initiates the deployment process.",
            "process": {
              "adds_new_entities": null,
              "description": "Processes the deployment of the environment."
            },
            "start_state": "initial",
            "end_state": "deployment_in_progress"
          },
          {
            "name": "complete_deployment",
            "description": "Completes the deployment process.",
            "process": {
              "adds_new_entities": null,
              "description": "Finalizes the deployment."
            },
            "start_state": "deployment_in_progress",
            "end_state": "deployment_completed"
          }
        ]
      }
    },
    {
      "entity_name": "user_app",
      "entity_source": "ENTITY_EVENT",
      "entity_type": "USER_APPLICATION",
      "entity_workflow": {
        "name": "user_app_workflow",
        "class_name": "com.cyoda.tdb.model.treenode.TreeNodeEntity",
        "transitions": [
          {
            "name": "start_user_app_deployment",
            "description": "Starts the user application deployment process.",
            "process": {
              "adds_new_entities": null,
              "description": "Processes the deployment of the user application."
            },
            "start_state": "initial",
            "end_state": "user_app_deployment_in_progress"
          },
          {
            "name": "complete_user_app_deployment",
            "description": "Completes the user application deployment process.",
            "process": {
              "adds_new_entities": null,
              "description": "Finalizes the user application deployment."
            },
            "start_state": "user_app_deployment_in_progress",
            "end_state": "user_app_deployment_completed"
          }
        ]
      }
    }
  ]
}
```

### Workflow Flowcharts

#### 1. Cyoda Environment Workflow

```mermaid
flowchart TD
  A[Initial State] -->|transition: start_deployment, processor: deploy_cyoda_env| B[Deployment In Progress]
  B -->|transition: complete_deployment, processor: finalize_deployment| C[Deployment Completed]
  %% decision point for completion (if necessary)
  B -->|criteria: criteria_name, environment_status equals "ready"| D1{Decision: Check Criteria}
  D1 -->|true| C
  D1 -->|false| E[Error: Criteria not met]
class A,B,C,D,D1 automated;
```

#### 2. User Application Workflow

```mermaid
flowchart TD
  A[Initial State] -->|transition: start_user_app_deployment, processor: deploy_user_app| B[User App Deployment In Progress]
  B -->|transition: complete_user_app_deployment, processor: finalize_user_app_deployment| C[User App Deployment Completed]
  %% decision point for completion (if necessary)
  B -->|criteria: criteria_name, app_status equals "ready"| D1{Decision: Check Criteria}
  D1 -->|true| C
  D1 -->|false| E[Error: Criteria not met]
class A,B,C,D,D1 automated;
```

### Explanation
- The JSON structure defines two main entities (`cyoda_env` and `user_app`) that will interact within the application. Each entity has its own workflow consisting of specific transitions representing states of the deployment process.
- The flowcharts capture the essential states and transitions of the workflows for both the environment and user application, demonstrating how the state machine logic is employed to handle the business logic through the integration with TeamCity.
- The workflows should ensure that each transition performs the necessary business logic to orchestrate interactions with the TeamCity server while respecting the lifecycle of the entities within the Cyoda architecture.