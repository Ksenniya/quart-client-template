[
    {
        "entity/prototype.py": "from quart import Quart, request, jsonify\nfrom quart_schema import QuartSchema\nimport aiohttp\nimport asyncio\nfrom app_init.app_init import entity_service\n\napp = Quart(__name__)\nQuartSchema(app)\n\ndef mock_teamcity_api(endpoint, method='GET', json=None):\n    async def inner():\n        await asyncio.sleep(1)\n        if method == 'POST':\n            return {'build_id': 'mock_build_id'}\n        elif method == 'GET':\n            return {'status': 'in_progress', 'repository_url': 'http://....', 'is_public': 'true'}\n    return inner()\n\n@app.route('/auth/login', methods=['POST'])\nasync def login():\n    data = await request.get_json()\n    username = data.get('username')\n    password = data.get('password')\n    return jsonify({'token': 'mock_token', 'message': 'Login successful'}), 200\n\n@app.route('/environments', methods=['POST'])\nasync def create_env():\n    data = await request.get_json()\n    user_name = data.get('user_name')\n    env_config = data.get('env_config')\n    entity_service.add_item(token=token, entity_model=\"environments\", entity_version=ENTITY_VERSION, entity=data)\n    response = await mock_teamcity_api('/app/rest/buildQueue', method='POST', json={'user_name': user_name})\n    return jsonify(response), 201\n\n@app.route('/deployments', methods=['POST'])\nasync def deploy_app():\n    data = await request.get_json()\n    repository_url = data.get('repository_url')\n    is_public = data.get('is_public')\n    response = await mock_teamcity_api('/app/rest/buildQueue', method='POST', json={'repository_url': repository_url, 'is_public': is_public})\n    return jsonify(response), 201\n\n@app.route('/environments/<id>/status', methods=['GET'])\nasync def get_env_status(id):\n    response = await mock_teamcity_api(f'/app/rest/buildQueue/id:{id}', method='GET')\n    return jsonify(response), 200\n\n@app.route('/environments/<id>/statistics', methods=['GET'])\nasync def get_env_statistics(id):\n    response = await mock_teamcity_api(f'/app/rest/builds/id:{id}/statistics/', method='GET')\n    return jsonify(response), 200\n\n@app.route('/deployments/<id>/cancel', methods=['POST'])\nasync def cancel_user_app(id):\n    data = await request.get_json()\n    comment = data.get('comment')\n    readd_into_queue = data.get('readdIntoQueue')\n    response = await mock_teamcity_api(f'/app/rest/builds/id:{id}', method='POST', json={'comment': comment, 'readdIntoQueue': readd_into_queue})\n    return jsonify({'message': 'Build canceled successfully'}), 200\n\nif __name__ == '__main__':\n    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)"
    }
]