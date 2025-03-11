import httpx
import logging

logger = logging.getLogger(__name__)

async def process_fetch_external(entity: dict):
    try:
        # Fetch external data using httpx
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get("https://jsonplaceholder.typicode.com/posts/1")
            response.raise_for_status()
            external_data = response.json()
        
        # Update the entity with fetched data
        entity["data"]["title"] = external_data.get("title", "")
        entity["data"]["body"] = external_data.get("body", "")
        # (Optional) Store external_data if needed for further processing
        entity["data"]["external_data"] = external_data
    except Exception as e:
        logger.error(f"Error fetching external data: {e}")
        entity["data"]["status"] = "error"
        entity["data"]["error_message"] = str(e)

async def process_combine_result(entity: dict):
    try:
        # Combine title and body to produce a processed result
        title = entity["data"].get("title", "").strip()
        body = entity["data"].get("body", "").strip()
        processed_result = f"Processed: {title} & {body}"
        entity["data"]["processedResult"] = processed_result
    except Exception as e:
        logger.error(f"Error combining results: {e}")
        entity["data"]["status"] = "error"
        entity["data"]["error_message"] = str(e)