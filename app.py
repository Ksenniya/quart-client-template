import asyncio
import logging

from quart import Quart

from common.grpc_client.grpc_client import grpc_stream
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token

app = Quart(__name__)

logging.basicConfig(level=logging.INFO)

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
