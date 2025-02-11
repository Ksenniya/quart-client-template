import asyncio
import logging

from quart import Quart
from quart_schema import QuartSchema
from common.grpc_client.grpc_client import grpc_stream
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token
#please update this line to your entity
from entity.cyoda_env.api import api_bp_cyoda_env
from entity.user_app.api import api_bp_user_app
from entity.cyoda_env_status.api import api_bp_cyoda_env_status
from entity.cyoda_env_statistics.api import api_bp_cyoda_env_statistics
from entity.user_app_status.api import api_bp_user_app_status
from entity.user_app_statistics.api import api_bp_user_app_statistics


logging.basicConfig(level=logging.INFO)

app = Quart(__name__)
QuartSchema(app)
app.register_blueprint(api_bp_cyoda_env, url_prefix='/api/cyoda_env')
app.register_blueprint(api_bp_user_app, url_prefix='/api/user_app')
app.register_blueprint(api_bp_cyoda_env_status, url_prefix='/api/cyoda_env_status')
app.register_blueprint(api_bp_cyoda_env_statistics, url_prefix='/api/cyoda_env_statistics')
app.register_blueprint(api_bp_user_app_status, url_prefix='/api/user_app_status')
app.register_blueprint(api_bp_user_app_statistics, url_prefix='/api/user_app_statistics')


@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))


@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

#put_application_code_here

if __name__ == '__main__':
    app.run()
