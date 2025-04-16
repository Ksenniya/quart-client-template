```python
import logging
from dataclasses import dataclass
from quart import Quart, jsonify, request
import httpx
from quart_schema import QuartSchema, validate_request, validate_querystring

app = Quart(__name__)
QuartSchema(app)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Local cache to mimic persistence
cat_data_cache = {}

# External API configuration
CATS_API_URL = "https://api.thecatapi.com/v1"  # Replace with the actual Cats API endpoint
API_KEY = "YOUR_API_KEY"  # TODO: Replace with your actual API key for authentication

@dataclass
class CatBreedRequest:
    breed: str

@dataclass
class CatImageResponse:
    image_url: str

@app.route('/api/cat-breeds', methods=['GET'])
async def get_cat_breeds():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CATS_API_URL}/breeds", headers={"x-api-key": API_KEY})
            response.raise_for_status()
            breeds = response.json()
            return jsonify({"breeds": [{"id": breed['id'], "name": breed['name']} for breed in breeds]})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve cat breeds"}), 500

@app.route('/api/random-cat', methods=['GET'])
async def get_random_cat():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CATS_API_URL}/images/search", headers={"x-api-key": API_KEY})
            response.raise_for_status()
            image_data = response.json()
            return jsonify({"image_url": image_data[0]['url']})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve random cat image"}), 500

@app.route('/api/fetch-cat-data', methods=['POST'])
@validate_request(CatBreedRequest)  # Validation should be last for POST requests
async def fetch_cat_data(data: CatBreedRequest):
    breed = data.breed
    # TODO: Validate the breed against a known list or handle errors
    if not breed:
        return jsonify({"error": "Breed is required"}), 400
    
    if breed in cat_data_cache:
        return jsonify({"data": cat_data_cache[breed]})

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CATS_API_URL}/breeds/{breed}", headers={"x-api-key": API_KEY})
            response.raise_for_status()
            breed_data = response.json()
            # Mocking the description and images for the prototype
            cat_data_cache[breed] = {
                "breed": breed_data['name'],
                "description": breed_data.get("description", "No description available."),  # TODO: Handle missing descriptions
                "images": breed_data.get("image", {}).get("url", [])
            }
            return jsonify({"data": cat_data_cache[breed]})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to fetch cat data"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```