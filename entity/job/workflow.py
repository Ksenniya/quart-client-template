import logging
from datetime import datetime

import httpx

# process_pets fetches pets data and updates the entity state.
async def process_pets(entity: dict):
    try:
        status = entity.get("fetchFilter", {}).get("status", "available")
        url = "https://petstore.swagger.io/v2/pet/findByStatus"
        params = {"status": status}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            pets_data = response.json()
        entity.setdefault("results", {})["pets"] = pets_data
        logging.info("Fetched %d pets.", len(pets_data) if isinstance(pets_data, list) else 0)
    except Exception as e:
        logging.exception(e)
        entity.setdefault("results", {})["pets"] = {"error": "Failed to fetch pets"}
    return entity

# process_orders fetches orders data and updates the entity state.
async def process_orders(entity: dict):
    try:
        url = "https://petstore.swagger.io/v2/store/inventory"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            orders_data = response.json()
        entity.setdefault("results", {})["orders"] = orders_data
        logging.info("Fetched orders inventory data.")
    except Exception as e:
        logging.exception(e)
        entity.setdefault("results", {})["orders"] = {"error": "Failed to fetch orders"}
    return entity

# process_users sets a placeholder for users data and updates the entity state.
async def process_users(entity: dict):
    try:
        entity.setdefault("results", {})["users"] = []
        logging.info("Users endpoint is not implemented; using placeholder.")
    except Exception as e:
        logging.exception(e)
        entity.setdefault("results", {})["users"] = {"error": "Failed to fetch users"}
    return entity

# process_summary calculates summary metrics based on fetched results,
# builds the final result, and updates the entity state.
async def process_summary(entity: dict):
    try:
        results = entity.get("results", {})
        pets = results.get("pets", [])
        orders = results.get("orders", {})
        users = results.get("users", [])
        summary = {
            "petCount": len(pets) if isinstance(pets, list) else 0,
            "orderCount": len(orders) if isinstance(orders, dict) else 0,
            "userCount": len(users) if isinstance(users, list) else 0,
        }
        final_result = {
            "resultId": entity.get("technicalId", "unknown"),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": results,
            "summary": summary
        }
        entity["result"] = final_result
        entity["status"] = "completed"
        entity["workflowProcessed"] = True
        entity["processedAt"] = datetime.utcnow().isoformat() + "Z"
    except Exception as e:
        logging.exception(e)
        entity["status"] = "failed"
        entity["error"] = str(e)
        entity["workflowProcessed"] = True
        entity["processedAt"] = datetime.utcnow().isoformat() + "Z"
    return entity
