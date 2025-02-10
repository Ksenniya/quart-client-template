# Here's the `api.py` file that implements the specified endpoints for the `user_app` entity in a Quart application with the use of a blueprint. Each endpoint corresponds to the HTTP method, and I have included both the POST and GET templates as per your request.
# 
# ```python
from quart import Blueprint, request, jsonify, abort
from common.service.entity_service_interface import EntityService

api_bp_user_app = Blueprint('api/user_app', __name__)

ENTITY_NAME = 'user_app'
ENTITY_VERSION = '1.0'  # Example version, replace with actual version as needed

@api_bp_user_app.route('/deploy/user_app', methods=['POST'])
async def deploy_user_app():
    cyoda_token = request.headers.get('Authorization')  # Assuming the token is passed in the headers
    if not cyoda_token:
        abort(401, 'Authorization token is required')
    
    data = await request.get_json()
    if not data:
        abort(400, 'Request body must be JSON')

    try:
        entity_service = EntityService()  # Replace this line with actual service initialization
        entity_id = await entity_service.add_item(cyoda_token, ENTITY_NAME, ENTITY_VERSION, data)
        return jsonify({'id': entity_id}), 201
    except Exception as e:
        abort(500, str(e))

@api_bp_user_app.route('/deploy/user_app/status/<int:id>', methods=['GET'])
async def get_user_app_status(id):
    cyoda_token = request.headers.get('Authorization')  # Assuming the token is passed in the headers
    if not cyoda_token:
        abort(401, 'Authorization token is required')

    try:
        entity_service = EntityService()  # Replace this line with actual service initialization
        entity_data = await entity_service.get_item(cyoda_token, ENTITY_NAME, ENTITY_VERSION, str(id))
        return jsonify(entity_data), 200
    except Exception as e:
        abort(500, str(e))

@api_bp_user_app.route('/deploy/cancel/user_app/<int:id>', methods=['POST'])
async def cancel_user_app(id):
    cyoda_token = request.headers.get('Authorization')  # Assuming the token is passed in the headers
    if not cyoda_token:
        abort(401, 'Authorization token is required')

    try:
        # Here, implement logic to cancel the user app build, this may involve a specific service method
        # Assuming `entity_service` has a method `cancel_item`
        entity_service = EntityService()  # Replace this line with actual service initialization
        await entity_service.cancel_item(cyoda_token, ENTITY_NAME, ENTITY_VERSION, str(id))
        return jsonify({'message': 'User app deployment canceled'}), 204
    except Exception as e:
        abort(500, str(e))

# ```
# 
# ### Explanation:
# 
# 1. **Blueprint Setup:** The blueprint for `user_app` is created with the name `api/user_app`.
# 
# 2. **Virtual Functions:** The `EntityService()` function shall be replaced with the actual implementation or injection of your service instance.
# 
# 3. **Authorization Handling:** The token is fetched from the headers, and if not present, a 401 Unauthorized error is returned.
# 
# 4. **Error Handling:** Each endpoint includes try-except blocks to catch and handle exceptions gracefully, returning a 500 Internal Server Error if an exception occurs.
# 
# 5. **Return Values:** 
#    - The POST endpoint for deploying a user app returns the id of the created user app with a status code of 201.
#    - The GET endpoint returns the status of the user app deployment with a 200 status code.
#    - The POST endpoint for cancellation responds with a 204 No Content status upon successful cancellation.
# 
# Make sure to implement the missing service methods in your `EntityService` class for the cancel operation as necessary.