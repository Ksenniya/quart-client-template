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
    # Example workflow function to process cat data
    cat_data['processed'] = True  # Modify the entity state as needed
    return cat_data

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
        # Check if breed data already exists
        breed_data = await entity_service.get_items_by_condition(
            token=cyoda_token,
            entity_model="cat_data_cache",
            entity_version=ENTITY_VERSION,
            condition={"breed": breed}
        )
        
        if breed_data:
            return jsonify({"data": breed_data[0]})

        # Fetch fresh data and store it
        breed_data = await entity_service.get_item(
            token=cyoda_token,
            entity_model="cat_breeds",
            entity_version=ENTITY_VERSION,
            technical_id=breed
        )

        cat_data = {
            "breed": breed_data['name'],
            "description": breed_data.get("description", "No description available."),
            "images": breed_data.get("image", {}).get("url", [])
        }
        
        # Store the data in the external service with a workflow function
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="cat_data_cache",
            entity_version=ENTITY_VERSION,
            entity=cat_data,
            workflow=process_cat_data  # Add the workflow function here
        )

        return jsonify({"data": cat_data})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to fetch cat data"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```