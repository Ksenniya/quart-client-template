import asyncio
import logging
import httpx

logger = logging.getLogger(__name__)

# Fetch current UTC datetime from external API and update entity state
async def process_fetch_time(entity: dict) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.get("http://worldtimeapi.org/api/timezone/Etc/UTC")
        response.raise_for_status()
        external_data = response.json()
    entity["current_datetime"] = external_data.get("datetime")

# Extract input data from entity and update entity state
async def process_extract_input(entity: dict) -> None:
    input_data = entity.get("inputData", "")
    entity["input_value"] = input_data

# Build the processing result and update entity state
async def process_build_result(entity: dict) -> None:
    current_datetime = entity.get("current_datetime", "")
    input_value = entity.get("input_value", "")
    result = f"Processed '{input_value}' at {current_datetime}"
    entity["result"] = result

# Set success state on entity after processing
async def process_set_success(entity: dict) -> None:
    entity["status"] = "completed"
    entity["workflowProcessed"] = True

# Set error state on entity in case of exception during processing
async def process_set_error(entity: dict) -> None:
    entity["result"] = None
    entity["status"] = "error"
    entity["workflowProcessed"] = False