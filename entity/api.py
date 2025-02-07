{
    "Environment": [
        {
            "api_endpoint": "/deploy/cyoda-env",
            "api_endpoint_complete_code": "async def deploy_cyoda_env():\n    data = await request.json\n    user_name = data.get('user_name')\n\n    if not user_name:\n        return jsonify({'error': 'user_name is required'}), 400\n    build_payload = {\n        'buildType': {\n            'id': 'KubernetesPipeline_CyodaSaas'\n        },\n        'properties': {\n            'property': [\n                {'name': 'user_defined_keyspace', 'value': user_name},\n                {'name': 'user_defined_namespace', 'value': user_name}\n            ]\n        }\n    }\n\n    async with httpx.AsyncClient() as client:\n        response = await client.post(f'{TEAMCITY_URL}/buildQueue', json=build_payload)\n        return jsonify(response.json()), response.status_code"
        },
        {
            "api_endpoint": "/deploy/user_app",
            "api_endpoint_complete_code": "async def deploy_user_app():\n    data = await request.json\n    repository_url = data.get('repository_url')\n    is_public = data.get('is_public')\n    if not repository_url:\n        return jsonify({'error': 'repository_url is required'}), 400\n    user_name = 'test_user'  # Simulating extracting a user name (should be from auth context)\n    build_payload = {\n        'buildType': {\n            'id': 'KubernetesPipeline_CyodaSaasUserEnv'\n        },\n        'properties': {\n            'property': [\n                {'name': 'user_defined_keyspace', 'value': user_name},\n                {'name': 'user_defined_namespace', 'value': user_name}\n            ]\n        }\n    }\n\n    async with httpx.AsyncClient() as client:\n        response = await client.post(f'{TEAMCITY_URL}/buildQueue', json=build_payload)\n        return jsonify(response.json()), response.status_code"
        }
    ],
    "Deployment": [
        {
            "api_endpoint": "/deploy/cyoda-env/status/<id>",
            "api_endpoint_complete_code": "async def cyoda_env_status(id):\n    async with httpx.AsyncClient() as client:\n        response = await client.get(f'{TEAMCITY_URL}/buildQueue/id:{id}')\n        return jsonify(response.json()), response.status_code"
        },
        {
            "api_endpoint": "/deploy/cyoda-env/statistics/<id>",
            "api_endpoint_complete_code": "async def cyoda_env_statistics(id):\n    async with httpx.AsyncClient() as client:\n        response = await client.get(f'{TEAMCITY_URL}/builds/id:{id}/statistics/')\n        return jsonify(response.json()), response.status_code"
        },
        {
            "api_endpoint": "/deploy/user_app/status/<id>",
            "api_endpoint_complete_code": "async def user_app_status(id):\n    async with httpx.AsyncClient() as client:\n        response = await client.get(f'{TEAMCITY_URL}/buildQueue/id:{id}')\n        return jsonify(response.json()), response.status_code"
        },
        {
            "api_endpoint": "/deploy/user_app/statistics/<id>",
            "api_endpoint_complete_code": "async def user_app_statistics(id):\n    async with httpx.AsyncClient() as client:\n        response = await client.get(f'{TEAMCITY_URL}/builds/id:{id}/statistics/')\n        return jsonify(response.json()), response.status_code"
        },
        {
            "api_endpoint": "/deploy/cancel/user_app/<id>",
            "api_endpoint_complete_code": "async def cancel_user_app(id):\n    cancel_payload = {\n        'comment': 'Canceling a queued build',\n        'readdIntoQueue': False\n    }\n\n    async with httpx.AsyncClient() as client:\n        response = await client.post(f'{TEAMCITY_URL}/builds/id:{id}', json=cancel_payload)\n        return jsonify(response.json()), response.status_code"
        }
    ],
    "BuildStatus": [
        {
            "api_endpoint": "/deploy/cyoda-env/status/<id>",
            "api_endpoint_complete_code": "async def cyoda_env_status(id):\n    async with httpx.AsyncClient() as client:\n        response = await client.get(f'{TEAMCITY_URL}/buildQueue/id:{id}')\n        return jsonify(response.json()), response.status_code"
        },
        {
            "api_endpoint": "/deploy/user_app/status/<id>",
            "api_endpoint_complete_code": "async def user_app_status(id):\n    async with httpx.AsyncClient() as client:\n        response = await client.get(f'{TEAMCITY_URL}/buildQueue/id:{id}')\n        return jsonify(response.json()), response.status_code"
        }
    ]
}