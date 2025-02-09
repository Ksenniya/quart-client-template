import asyncio
import logging

from quart import Quart
from quart_schema import QuartSchema
from common.grpc_client.grpc_client import grpc_stream
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token
#please update this line to your entity
from entity.cyoda_environment_deployment.api import api_bp_cyoda_environment_deployment
from entity.user_application_deployment.api import api_bp_user_application_deployment


logging.basicConfig(level=logging.INFO)

app = Quart(__name__)
QuartSchema(app)
app.register_blueprint(api_bp_cyoda_environment_deployment, url_prefix='/api/cyoda_environment_deployment')
app.register_blueprint(api_bp_user_application_deployment, url_prefix='/api/user_application_deployment')


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
