import asyncio
import logging
import httpx  # Make sure httpx is installed
from quart import Quart, jsonify
from quart_schema import QuartSchema
from common.grpc_client.grpc_client import grpc_stream
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service  # Import entity_service
# please update this line to your entity
from entity.ENTITY_NAME_VAR.api import api_bp_ENTITY_NAME_VAR

logging.basicConfig(level=logging.INFO)

app = Quart(__name__)
QuartSchema(app)
app.register_blueprint(api_bp_ENTITY_NAME_VAR, url_prefix='/api/ENTITY_NAME_VAR')

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

# New GET endpoint to fetch post data
@app.route('/api/posts/1', methods=['GET'])
async def get_post():
    async with httpx.AsyncClient() as client:
        response = await client.get('https://jsonplaceholder.typicode.com/posts/1')
        response.raise_for_status()  # Raise an exception for HTTP errors
        post_data = response.json()

        # Here we add the post data to the entity service
        id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="app.py",
            entity_version=ENTITY_VERSION,
            entity=post_data  # Assuming the post data is a valid entity
        )

        return jsonify({"id": id}), 201

# put_application_code_here

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)