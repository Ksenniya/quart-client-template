import asyncio
import logging

from quart import Quart
from quart_schema import QuartSchema
from common.grpc_client.grpc_client import grpc_stream
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token
#please update this line to your entity
from entity.auth.api import api_bp_auth
from entity.environment.api import api_bp_environment
from entity.user_app.api import api_bp_user_app
from entity.status.api import api_bp_status
from entity.statistic.api import api_bp_statistic
from entity.ENTITY_NAME_VAR.api import api_bp_ENTITY_NAME_VAR

logging.basicConfig(level=logging.INFO)

app = Quart(__name__)
QuartSchema(app)
app.register_blueprint(api_bp_auth, url_prefix='/api/auth')
app.register_blueprint(api_bp_environment, url_prefix='/api/environment')
app.register_blueprint(api_bp_user_app, url_prefix='/api/user_app')
app.register_blueprint(api_bp_status, url_prefix='/api/status')
app.register_blueprint(api_bp_statistic, url_prefix='/api/statistic')
app.register_blueprint(api_bp_ENTITY_NAME_VAR, url_prefix='/api/ENTITY_NAME_VAR')

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
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)