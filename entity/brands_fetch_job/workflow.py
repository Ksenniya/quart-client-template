import asyncio
import datetime
import aiohttp
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request
from common.config.config import ENTITY_VERSION
from app_init.app_init import cyoda_token, entity_service
from common.repository.cyoda.cyoda_init import init_cyoda

# Business logic for processing a single brand entity.
async def process_brand(entity: dict):
    try:
        # Add a timestamp to indicate when the brand entity was processed.
        entity["processedAt"] = datetime.datetime.utcnow().isoformat()
        # Additional asynchronous operations to enrich the brand entity can be added here.
    except Exception as e:
        # In case of error, update the entity state accordingly.
        entity["processingError"] = str(e)
    return entity

# Workflow orchestration for fetching and processing brands.
async def process_brands_fetch_job(job_entity: dict):
    try:
        external_api_url = 'https://api.practicesoftwaretesting.com/brands'
        async with aiohttp.ClientSession() as session:
            async with session.get(external_api_url, headers={"accept": "application/json"}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    processed_count = 0
                    for item in data:
                        try:
                            await process_brand(item)
                            processed_count += 1
                        except Exception as inner_e:
                            # Attach error information to the brand item.
                            item["processingError"] = str(inner_e)
                    # Update the job entity state as completed.
                    job_entity["status"] = "completed"
                    job_entity["completedAt"] = datetime.datetime.utcnow().isoformat()
                    job_entity["processedCount"] = processed_count
                else:
                    # Update the job entity state as failed if external API call is unsuccessful.
                    job_entity["status"] = "failed"
                    job_entity["error"] = f"External API error: HTTP {resp.status}"
    except Exception as e:
        # Catch any unexpected errors and update the job entity accordingly.
        job_entity["status"] = "failed"
        job_entity["error"] = str(e)
    return job_entity