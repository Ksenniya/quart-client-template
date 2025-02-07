# Certainly! Let’s refactor the code to move the business logic related to creating and deploying environments into separate processor functions. This will enhance the separation of concerns and make the code easier to maintain and test. 
# 
# ### Updated `api.py` Code
# 
# Here’s how you can restructure the `deploy_cyoda_env` function and create a separate processor for handling business logic.
# 
# ```python
from quart import Quart, request, jsonify
import httpx

app = Quart(__name__)

TEAMCITY_URL = "https://teamcity.cyoda.org/app/rest"


async def validate_environment_info(user_name):
    if not user_name:
        return {"error": "user_name is required"}, 400
    return None, None


async def create_build_payload(user_name):
    return {
        'buildType': {
            'id': 'KubernetesPipeline_CyodaSaas'
        },
        'properties': {
            'property': [
                {'name': 'user_defined_keyspace', 'value': user_name},
                {'name': 'user_defined_namespace', 'value': user_name}
            ]
        }
    }


async def deploy_build(build_payload):
    async with httpx.AsyncClient() as client:
        response = await client.post(f'{TEAMCITY_URL}/buildQueue', json=build_payload)
        return response.json(), response.status_code


@app.route('/deploy/cyoda-env', methods=['POST'])
async def deploy_cyoda_env():
    data = await request.json
    user_name = data.get('user_name')

    # Validate environment information
    error_response, status_code = await validate_environment_info(user_name)
    if error_response:
        return jsonify(error_response), status_code

    # Create build payload
    build_payload = await create_build_payload(user_name)

    # Deploy to TeamCity
    response_json, status_code = await deploy_build(build_payload)
    return jsonify(response_json), status_code

# The other API endpoints would need similar refactoring, moving business logic out into processor functions.

if __name__ == "__main__":
    app.run()
# ```
# 
# ### Flowchart Representation
# 
# To represent the steps in the deployment workflow, you can consider the following flowchart based on the Mermaid syntax you have provided. This flowchart illustrates the logical steps taken during the environment creation and deployment process.
# 
# ```mermaid
# flowchart TD
#     A[Create Environment] --> B{Environment Info Valid?}
#     B -->|Yes| C[Initiate Environment]
#     B -->|No| D[Return Error]
#     C --> E[Deploy to TeamCity]
#     E --> F{Deployment Status?}
#     F -->|Success| G[Update Deployment Status]
#     F -->|Failed| H[Notify User]
# ```
# 
# ### Explanation of the Code Changes
# 
# 1. **Validation Logic**: The environment validation logic has been moved to the `validate_environment_info` function. This checks for the presence of `user_name` and returns appropriate error messages if validation fails.
# 
# 2. **Build Payload Creation**: The logic to create the build payload has been moved to the `create_build_payload` function.
# 
# 3. **Deployment Handling**: The actual deployment to TeamCity is now encapsulated in the `deploy_build` function, which takes care of sending the request.
# 
# 4. **Main Endpoint**: The `deploy_cyoda_env` function now simply orchestrates these other functions and handles the resulting responses.
# 
# This structure will allow for easier updates and unit testing of each piece of business logic without affecting the overall API endpoints directly. Let me know if you need further changes or additional functionality!