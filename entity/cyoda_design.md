{
    "entities": [
        {
            "type": "User",
            "properties": {
                "user_id": "string",
                "user_name": "string",
                "email": "string",
                "token": "string"
            }
        },
        {
            "type": "Deployment",
            "properties": {
                "deployment_id": "string",
                "user_id": "string",
                "repository_url": "string",
                "is_public": "boolean",
                "status": "string",
                "timestamp": "string",
                "duration": "string",
                "errors": "number",
                "success": "boolean"
            }
        },
        {
            "type": "Build",
            "properties": {
                "build_id": "string",
                "build_type": "string",
                "properties": {
                    "user_defined_keyspace": "string",
                    "user_defined_namespace": "string"
                },
                "status": "string",
                "created_timestamp": "string"
            }
        }
    ],
    "workflows": [
        {
            "name": "DeploymentWorkflow",
            "transitions": [
                {
                    "from": "Pending",
                    "to": "InProgress",
                    "action": "startDeployment",
                    "processor": "start_deployment_lambda"
                },
                {
                    "from": "InProgress",
                    "to": "Successful",
                    "action": "completeDeployment",
                    "processor": "complete_deployment_lambda"
                },
                {
                    "from": "InProgress",
                    "to": "Failed",
                    "action": "failDeployment",
                    "processor": "fail_deployment_lambda"
                },
                {
                    "from": "InProgress",
                    "to": "Cancelled",
                    "action": "cancelDeployment",
                    "processor": "cancel_deployment_lambda"
                }
            ]
        }
    ]
}