# ```python
import asyncio
import logging
import aiohttp
import unittest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = "https://raw.githubusercontent.com/Cyoda-platform/cyoda-ai/refs/heads/ai-2.x/data/test-inputs/v1/connections/london_houses.csv"

async def fetch_data() -> list:
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(API_URL) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.error(f"Error fetching data: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Exception occurred: {str(e)}")
            return None

async def ingest_data() -> list:
    data = await fetch_data()
    if data is None:
        logger.error("No data received for ingestion.")
        return []

    # Process and map the CSV data to the entity structure
    lines = data.splitlines()
    header = lines[0].split(",")
    property_data = lines[1].split(",")

    mapped_data = {
        "property_details": {
            "address": property_data[0],
            "neighborhood": property_data[1],
            "bedrooms": int(property_data[2]),
            "bathrooms": int(property_data[3]),
            "square_meters": int(property_data[4]),
            "building_age": int(property_data[5]),
            "garden": property_data[6],
            "garage": property_data[7],
            "floors": int(property_data[8]),
            "property_type": property_data[9],
            "heating_type": property_data[10],
            "balcony": property_data[11],
            "interior_style": property_data[12],
            "view": property_data[13],
            "materials": property_data[14],
            "building_status": property_data[15],
            "price": int(property_data[16])
        }
    }

    return [mapped_data]

class TestDataIngestion(unittest.TestCase):

    def test_ingest_data_success(self):
        result = asyncio.run(ingest_data())

        # Assertions to check that data is mapped correctly
        self.assertTrue(len(result) > 0)
        self.assertEqual(result[0]["property_details"]["address"], "78 Regent Street")
        self.assertEqual(result[0]["property_details"]["neighborhood"], "Notting Hill")
        self.assertEqual(result[0]["property_details"]["bedrooms"], 2)
        self.assertEqual(result[0]["property_details"]["bathrooms"], 3)
        self.assertEqual(result[0]["property_details"]["square_meters"], 179)
        self.assertEqual(result[0]["property_details"]["building_age"], 72)
        self.assertEqual(result[0]["property_details"]["garden"], "No")
        self.assertEqual(result[0]["property_details"]["garage"], "No")
        self.assertEqual(result[0]["property_details"]["floors"], 3)
        self.assertEqual(result[0]["property_details"]["property_type"], "Semi-Detached")
        self.assertEqual(result[0]["property_details"]["heating_type"], "Electric Heating")
        self.assertEqual(result[0]["property_details"]["balcony"], "High-level Balcony")
        self.assertEqual(result[0]["property_details"]["interior_style"], "Industrial")
        self.assertEqual(result[0]["property_details"]["view"], "Garden")
        self.assertEqual(result[0]["property_details"]["materials"], "Marble")
        self.assertEqual(result[0]["property_details"]["building_status"], "Renovated")
        self.assertEqual(result[0]["property_details"]["price"], 2291200)

if __name__ == "__main__":
    unittest.main()
# ``` 
# 
# ### Explanation of the Code
# 
# 1. **`fetch_data()` Function**:
#    - This asynchronous function makes a GET request to the specified API URL to retrieve the CSV data for London houses.
#    - It returns the raw CSV content as text if the request is successful (HTTP status 200).
# 
# 2. **`ingest_data()` Function**:
#    - This public function orchestrates the data ingestion process by calling `fetch_data()` to retrieve the data.
#    - It processes the CSV data, mapping it into the specified entity structure for property details.
#    - The mapped data is returned as a list containing the processed entity.
# 
# 3. **Unit Tests**:
#    - The `TestDataIngestion` class uses the `unittest` framework to verify the functionality of the `ingest_data` function.
#    - The `test_ingest_data_success` method checks that the data is mapped correctly, asserting various attributes of the property details.
# 
# This code is structured to allow immediate testing of the data ingestion functionality in an isolated environment without the need for mocking external services. If you have any further requests or need modifications, please let me know! 😊