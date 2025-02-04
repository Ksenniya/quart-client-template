# Here's the implementation of the processor function `ingest_raw_data` for the `data_ingestion_job`. This function will reuse the existing `ingest_data` connection function, save the result to the corresponding raw data entity, and include unit tests to validate the functionality.
# 
# ```python
import logging
import asyncio
from app_init.app_init import entity_service
from entity.raw_data_entity.connections.connections import ingest_data as ingest_raw_data_connection
from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ingest_raw_data(meta, data):
    logger.info("Starting data ingestion process.")
    try:
        # Call the reusable ingest_data function
        raw_data = await ingest_raw_data_connection()

        if not raw_data:
            logger.error("No raw data received for ingestion.")
            raise ValueError("No data received for ingestion.")

        # Save the raw data entity
        raw_data_entity_id = await entity_service.add_item(
            meta["token"], "raw_data_entity", ENTITY_VERSION, raw_data
        )

        # Update the data with the raw data entity ID
        data["raw_data_entity"] = {"technical_id": raw_data_entity_id, "records": raw_data}
        logger.info(f"Raw data entity saved successfully with ID: {raw_data_entity_id}")
    except Exception as e:
        logger.error(f"Error in ingest_raw_data: {e}")
        raise


# Testing with Mocks
import unittest
from unittest.mock import patch

class TestDataIngestionJob(unittest.TestCase):

    @patch("workflow.ingest_raw_data_connection")
    @patch("app_init.app_init.entity_service.add_item")
    def test_ingest_raw_data(self, mock_add_item, mock_ingest_data):
        mock_ingest_data.return_value = [
            {
                "address": "78 Regent Street",
                "neighborhood": "Notting Hill",
                "bedrooms": 2,
                "bathrooms": 3,
                "square_meters": 179,
                "building_age": 72,
                "garden": "No",
                "garage": "No",
                "floors": 3,
                "property_type": "Semi-Detached",
                "heating_type": "Electric Heating",
                "balcony": "High-level Balcony",
                "interior_style": "Industrial",
                "view": "Garden",
                "materials": "Marble",
                "building_status": "Renovated",
                "price": 2291200
            }
        ]
        mock_add_item.return_value = "raw_data_entity_id"

        meta = {"token": "test_token"}
        data = {}

        asyncio.run(ingest_raw_data(meta, data))

        mock_add_item.assert_called_once_with(
            meta["token"], "raw_data_entity", ENTITY_VERSION, mock_ingest_data.return_value
        )

if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation of the Code
# 
# 1. **`ingest_raw_data` Function**:
#    - This function is responsible for orchestrating the data ingestion process.
#    - It calls the reusable `ingest_data` function to fetch raw data related to London houses.
#    - The fetched raw data is then saved to the `raw_data_entity`, and its technical ID is updated in the `data` object.
# 
# 2. **Unit Tests**:
#    - The `TestDataIngestionJob` class contains tests to validate the functionality of the `ingest_raw_data` function.
#    - The `test_ingest_raw_data` method mocks the external service calls for data ingestion and entity saving, ensuring that the function behaves as expected without relying on actual implementations.
# 
# This implementation allows for the immediate testing of the data ingestion functionality in an isolated environment, ensuring that the components work together seamlessly. If you have any further questions or need modifications, please let me know! 😊