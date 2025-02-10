{
    "primary_entities": [
        {
            "entity_name": "cyoda_env",
            "endpoints": {
                "POST": [
                    {
                        "endpoint": "/deploy/cyoda-env",
                        "description": "Deploys the Cyoda environment.",
                        "suggested_workflow": [
                            {
                                "start_state": "init",
                                "end_state": "deployed",
                                "action": "deploy_cyoda_env",
                                "complete_code_for_action_derived_from_the_prototype": "data = await request.get_json() \nuser_name = data.get(\"user_name\")\npayload = {\"buildType\": {\"id\": \"KubernetesPipeline_CyodaSaas\"}, \"properties\": {\"property\": [{\"name\": \"user_defined_keyspace\", \"value\": user_name}, {\"name\": \"user_defined_namespace\", \"value\": user_name},]}}}\nasync with aiohttp.ClientSession() as session:\n    async with session.post(f\"{TEAMCITY_URL}/buildQueue\", json=payload) as response:\n        response_data = await response.json()",
                                "description": "Handles the deployment of the Cyoda environment.",
                                "secondary_entities": []
                            }
                        ]
                    }
                ],
                "GET": []
            }
        },
        {
            "entity_name": "user_app",
            "endpoints": {
                "POST": [
                    {
                        "endpoint": "/deploy/user_app",
                        "description": "Deploys the user application.",
                        "suggested_workflow": [
                            {
                                "start_state": "init",
                                "end_state": "deployed",
                                "action": "deploy_user_app",
                                "complete_code_for_action_derived_from_the_prototype": "data = await request.get_json()\nrepository_url = data.get(\"repository_url\")\nis_public = data.get(\"is_public\")\nuser_name = \"test\"  # Placeholder\npayload = {\"buildType\": {\"id\": \"KubernetesPipeline_CyodaSaasUserEnv\"}, \"properties\": {\"property\": [{\"name\": \"user_defined_keyspace\", \"value\": user_name}, {\"name\": \"user_defined_namespace\", \"value\": user_name},]}}}\nasync with aiohttp.ClientSession() as session:\n    async with session.post(f\"{TEAMCITY_URL}/buildQueue\", json=payload) as response:\n        response_data = await response.json()",
                                "description": "Handles the deployment of the user application.",
                                "secondary_entities": []
                            }
                        ]
                    }
                ],
                "GET": []
            }
        },
        {
            "entity_name": "cancel_user_app",
            "endpoints": {
                "POST": [
                    {
                        "endpoint": "/deploy/cancel/user_app/<int:id>",
                        "description": "Cancels a queued user application deployment.",
                        "suggested_workflow": [
                            {
                                "start_state": "in_queue",
                                "end_state": "canceled",
                                "action": "cancel_user_app",
                                "complete_code_for_action_derived_from_the_prototype": "cancel_payload = {\"comment\": \"Canceling a queued build\", \"readdIntoQueue\": False}\nasync with aiohttp.ClientSession() as session:\n    async with session.post(f\"{TEAMCITY_URL}/builds/id:{id}\", json=cancel_payload) as response:\n        response_data = await response.json()",
                                "description": "Handles the cancellation of a queued user application deployment.",
                                "secondary_entities": []
                            }
                        ]
                    }
                ],
                "GET": []
            }
        }
    ],
    "secondary_entities": [
        {
            "entity_name": "cyoda_env_status",
            "endpoints": {
                "GET": [
                    {
                        "endpoint": "/deploy/cyoda-env/status/<int:id>",
                        "description": "Retrieves the status of the Cyoda environment deployment."
                    }
                ]
            }
        },
        {
            "entity_name": "user_app_status",
            "endpoints": {
                "GET": [
                    {
                        "endpoint": "/deploy/user_app/status/<int:id>",
                        "description": "Retrieves the status of the user application deployment."
                    }
                ]
            }
        }
    ]
}