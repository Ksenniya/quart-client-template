import asyncio
import logging
import aiohttp

from quart import Quart, jsonify
from quart_schema import QuartSchema
from common.grpc_client.grpc_client import grpc_stream
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token
from entity.my_entity.api import api_bp_my_entity

logging.basicConfig(level=logging.INFO)

app = Quart(__name__)
QuartSchema(app)
app.register_blueprint(api_bp_my_entity, url_prefix='/api/my_entity')

@app.before_serving
async def startup():
    try:
        await init_cyoda(cyoda_token)
        app.background_task = asyncio.create_task(grpc_stream(cyoda_token))
    except Exception as e:
        logging.error(f'Error during startup: {e}')

@app.after_serving
async def shutdown():
    if hasattr(app, 'background_task'):
        app.background_task.cancel()
        try:
            await app.background_task
        except Exception as e:
            logging.error(f'Error during shutdown: {e}')

@app.route('/store/inventory', methods=['GET'])
async def get_inventory():
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.example.com/store/inventory', headers={'api_key': 'special-key'}) as response:
            inventory = await response.json()
            return jsonify(inventory)

#put_application_code_here

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)