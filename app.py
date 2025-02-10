import asyncio
import logging

from quart import Quart
from quart_schema import QuartSchema
from common.grpc_client.grpc_client import grpc_stream
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token
#please update this line to your entity
from entity.analyze_data.api import api_bp_analyze_data
from entity.save_report.api import api_bp_save_report
from entity.download_data.api import api_bp_download_data


logging.basicConfig(level=logging.INFO)

app = Quart(__name__)
QuartSchema(app)
app.register_blueprint(api_bp_analyze_data, url_prefix='/api/analyze_data')
app.register_blueprint(api_bp_save_report, url_prefix='/api/save_report')
app.register_blueprint(api_bp_download_data, url_prefix='/api/download_data')


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
