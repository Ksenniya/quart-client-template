```python
import logging
from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

app = Quart(__name__)
QuartSchema(app)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@dataclass
class CatBreedRequest:
    breed: str

async def process_cat_data(cat_data):
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
    except Exception as e:
        logger.exception(e)

async def fetch_and_cache_cat_data(breed):
    try:
        # Check if breed data already exists
        breed_data = await entity_service.get_items_by_condition(
            token=cyoda_token,
            entity_model="cat_data_cache",
            entity_version=ENTITY_VERSION,
            condition={"breed": breed}
        )
        
        if breed_data:
            return breed_data[0]  # Return cached data if available

        # Fetch fresh data
        breed_data = await entity_service.get_item(
            token=cyoda_token,
            entity_model="cat_breeds",
            entity_version=ENTITY_VERSION,
            technical_id=breed
        )

        return breed_data
    except Exception as e:
        logger.exception(e)
        return None

@app.route('/api/cat-breeds', methods=['GET'])
async def get_cat_breeds():
    try:
        breeds = await entity_service.get_items(
            token=cyoda_token,
            entity_model="cat_breeds",
            entity_version=ENTITY_VERSION,
        )
        return jsonify({"breeds": [{"id": breed['id'], "name": breed['name']} for breed in breeds]})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve cat breeds"}), 500

@app.route('/api/random-cat', methods=['GET'])
async def get_random_cat():
    try:
        image_data = await entity_service.get_items(
            token=cyoda_token,
            entity_model="random_cats",
            entity_version=ENTITY_VERSION,
        )
        return jsonify({"image_url": image_data[0]['url']})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve random cat image"}), 500

@app.route('/api/fetch-cat-data', methods=['POST'])
@validate_request(CatBreedRequest)  # Validation should be last for POST requests
async def fetch_cat_data(data: CatBreedRequest):
    breed = data.breed
    if not breed:
        return jsonify({"error": "Breed is required"}), 400

    try:
        # Fetch and cache the data in the external service with a workflow function
        cat_data = {
            "breed": breed,
        }
        
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="cat_data_cache",
            entity_version=ENTITY_VERSION,
            entity=cat_data,
            workflow=process_cat_data  # Add the workflow function here
        )

        # Fetch and cache additional breed data
        cached_data = await fetch_and_cache_cat_data(breed)
        if cached_data:
            return jsonify({"data": cached_data})

        return jsonify({"error": "Failed to fetch cat data"}), 500

    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to fetch cat data"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```