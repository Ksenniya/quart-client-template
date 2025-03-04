import asyncio
import logging
import datetime
import httpx

logger = logging.getLogger(__name__)

# Business logic: Call external API to fetch and attach external calculation data into the order entity.
async def process_fetch_external_calculation(order: dict):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("https://petstore.swagger.io/v2/store/order", json=order)
            response.raise_for_status()
            calculation_data = response.json()
    except Exception as e:
        logger.exception(e)
        calculation_data = {"calculation": "default value"}
    order["externalCalculation"] = calculation_data
    return order

# Business logic: Set processed timestamp on the order entity.
async def process_set_processed_timestamp(order: dict):
    order["processedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    return order