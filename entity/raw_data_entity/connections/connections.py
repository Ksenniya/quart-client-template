# ```python
import asyncio
import logging
import aiohttp
import unittest
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = "https://fakerestapi.azurewebsites.net/api/v1/Activities"

async def fetch_data() -> List[Dict]:
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(API_URL, headers={"accept": "text/plain; v=1.0"}) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Error fetching data: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Exception occurred: {str(e)}")
            return []

async def ingest_data() -> List[Dict]:
    data = await fetch_data()
    if not data:
        logger.error("No data received for ingestion.")
        return []

    # Map raw data to the entity structure
    mapped_data = [
        {
            "id": activity["id"],
            "title": activity["title"],
            "due_date": activity["dueDate"],
            "completed": activity["completed"]
        } for activity in data
    ]

    return mapped_data

class TestDataIngestion(unittest.TestCase):
    def test_ingest_data_success(self):
        # Run the ingest_data function
        result = asyncio.run(ingest_data())

        # Assertions to check that data is mapped correctly
        self.assertTrue(len(result) > 0)
        self.assertIsInstance(result[0], dict)
        self.assertIn("id", result[0])
        self.assertIn("title", result[0])
        self.assertIn("due_date", result[0])
        self.assertIn("completed", result[0])

if __name__ == "__main__":
    unittest.main()
# ``` 
# 
# ### Explanation of the Code
# 1. **`fetch_data` Function**: This asynchronous function sends a GET request to the provided API URL to retrieve data. If the request is successful (HTTP status 200), it returns the JSON response; otherwise, it logs an error.
# 
# 2. **`ingest_data` Function**:
#    - Calls `fetch_data` to get the data.
#    - If data is received, it maps the raw data to the required entity structure by creating a list of dictionaries with the specified keys.
#    - Returns the mapped data.
# 
# 3. **Unit Tests**:
#    - The `TestDataIngestion` class contains a method to test the `ingest_data` function.
#    - It verifies that the function processes the data correctly and that the expected keys exist in the resulting data structure.
#    
# This setup allows the user to test the data fetching and mapping process in an isolated environment.