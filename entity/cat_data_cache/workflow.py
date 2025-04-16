import logging
from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_fetch_breed_data(cat_data):
    # Fetch additional breed data and modify the entity state
    try:
        breed_data = await entity_service.get_items_by_condition(
            token=cyoda_token,
            entity_model="cat_breeds",
            entity_version=ENTITY_VERSION,
            condition={"name": cat_data['breed']}
        )

        if breed_data:
            # Modify the cat_data with additional information
            cat_data['description'] = breed_data[0].get("description", "No description available.")
            cat_data['images'] = breed_data[0].get("image", {}).get("url", [])
            cat_data['processed'] = True  # Mark as processed
        else:
            cat_data['description'] = "Breed not found."
            cat_data['images'] = []
            cat_data['processed'] = False  # Mark as not processed if breed not found
    except Exception as e:
        logger.exception(e)
        cat_data['error'] = "Error processing cat data."