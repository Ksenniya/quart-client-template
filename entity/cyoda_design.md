Certainly! Below are example JSON data structures representing the entities and workflows for your application to be migrated to Cyoda Cloud.

### Entities

1. **User** Entity
   ```json
   {
       "id": "user_001",
       "user_name": "test_user",
       "access_token": "Bearer example_token",
       "created_at": "2023-10-01T10:00:00Z",
       "updated_at": "2023-10-01T10:15:00Z"
   }
   ```

2. **Deployment** Entity
   ```json
   {
       "id": "deploy_001",
       "user_id": "user_001",
       "repository_url": "http://example.com/repo.git",
       "is_public": true,
       "build_id": "12345",
       "status": "running",
       "created_at": "2023-10-01T10:05:00Z",
       "updated_at": "2023-10-01T10:15:00Z"
   }
   ```

3. **Build Status** Entity
   ```json
   {
       "id": "status_001",
       "deployment_id": "deploy_001",
       "status": "success",
       "build_id": "12345",
       "statistics": {
           "duration": "10m",
           "success_rate": 100,
           "failure_rate": 0
       },
       "created_at": "2023-10-01T10:15:00Z"
   }
   ```

4. **Statistics** Entity
   ```json
   {
       "id": "stats_001",
       "deployment_id": "deploy_001",
       "build_id": "12345",
       "data": {
           "cpu_usage": "75%",
           "memory_usage": "512MB",
           "disk_space": "2GB"
       },
       "created_at": "2023-10-01T10:15:00Z"
   }
   ```

5. **Cancellation** Entity
   ```json
   {
       "id": "cancel_001",
       "deployment_id": "deploy_001",
       "comment": "Canceling a queued build",
       "readd_into_queue": false,
       "status": "canceled",
       "created_at": "2023-10-01T10:20:00Z"
   }
   ```

### Workflows

1. **Deployment Workflow**
   - **States**
     - waitingForApproval
     - inProgress
     - completed
     - failed
     - canceled
   - **Transitions**
     - submit → inProgress (Trigger: Deploy Application)
     - timeout → failed (Trigger: Build Failure Timeout)
     - complete → completed (Trigger: Build Success)
     - cancel → canceled (Trigger: User Cancel Request)

   ```json
   {
       "id": "workflow_deployment",
       "name": "Deployment Workflow",
       "initial_state": "waitingForApproval",
       "states": [
           "waitingForApproval",
           "inProgress",
           "completed",
           "failed",
           "canceled"
       ],
       "transitions": [
           {
               "from": "waitingForApproval",
               "to": "inProgress",
               "action": "submit",
               "processor": "deployApplication"
           },
           {
               "from": "inProgress",
               "to": "failed",
               "action": "timeout",
               "processor": "handleTimeout"
           },
           {
               "from": "inProgress",
               "to": "completed",
               "action": "complete",
               "processor": "handleCompletion"
           },
           {
               "from": "inProgress",
               "to": "canceled",
               "action": "cancel",
               "processor": "handleCancellation"
           }
       ]
   }
   ```

### Example Workflow Transition Triggered Events

- "deployApplication" could invoke a Lambda function that starts the application deployment process.
- "handleTimeout" may trigger actions like notifying the user or logging the event.
- "handleCompletion" could store the final build status and associated metrics.
- "handleCancellation" would manage cleanup or rollback actions if necessary.

These entities and workflows should help in structuring your application for migration to Cyoda Cloud and facilitate improved scalability, reliability, and performance.