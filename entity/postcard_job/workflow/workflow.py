# Sure! I'll generate the processor functions for `postcard_job`, specifically `process_create_postcard` and `process_send_postcard`. I'll ensure to reuse the functions available in the codebase and include logic to save the dependent entities: `postcard_entity` and `delivery_status_entity`. Additionally, I'll create tests with mocks for external services or functions. Let's get started!
# 
# ```python
import logging
import asyncio
from app_init.app_init import entity_service
from entity.raw_data_entity.connections.connections import ingest_data as ingest_raw_data
from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def process_create_postcard(meta, data):
    """Process to create a postcard from user input."""
    logger.info("Starting postcard creation process.")
    try:
        # Simulate postcard creation logic
        postcard_data = {
            "postcard_id": data["job_id"],
            "user_id": data["user_id"],
            "image_url": data["request_parameters"]["image_url"],
            "message": data["request_parameters"]["message"],
            "created_at": data["created_at"],
            "status": "pending"
        }

        # Save postcard entity
        postcard_entity_id = await entity_service.add_item(
            meta["token"],
            "postcard_entity",
            ENTITY_VERSION,
            postcard_data
        )

        logger.info(f"Postcard entity saved successfully with ID: {postcard_entity_id}")

    except Exception as e:
        logger.error(f"Error in process_create_postcard: {e}")
        raise


async def process_send_postcard(meta, data):
    """Process to send the postcard."""
    logger.info("Starting postcard sending process.")
    try:
        # Simulate sending postcard logic
        delivery_status_data = {
            "delivery_status_id": data["job_id"],
            "postcard_id": data["job_id"],
            "status": "sent",
            "recipient": {
                "name": data["request_parameters"].get("recipient_name", "Unknown"),
                "address": data["request_parameters"]["recipient_address"],
                "email": data["request_parameters"].get("recipient_email", "unknown@example.com")
            },
            "sent_date": data["created_at"],
            "estimated_delivery_date": "2023-10-05T15:00:00Z",  # Example estimation
            "tracking_number": f"TRK{data['job_id']}",
            "delivery_updates": [],
            "request_parameters": {
                "postcard_id": data["job_id"],
                "user_id": data["user_id"],
                "action": "send_postcard"
            }
        }

        # Save delivery status entity
        delivery_status_entity_id = await entity_service.add_item(
            meta["token"],
            "delivery_status_entity",
            ENTITY_VERSION,
            delivery_status_data
        )

        logger.info(f"Delivery status entity saved successfully with ID: {delivery_status_entity_id}")

    except Exception as e:
        logger.error(f"Error in process_send_postcard: {e}")
        raise


# Testing with Mocks
import unittest
from unittest.mock import patch


class TestPostcardJob(unittest.TestCase):

    @patch("app_init.app_init.entity_service.add_item")
    def test_process_create_postcard(self, mock_add_item):
        mock_add_item.return_value = "postcard_entity_id"

        meta = {"token": "test_token"}
        data = {
            "job_id": "job_001",
            "user_id": "12345",
            "request_parameters": {
                "image_url": "https://example.com/image.jpg",
                "message": "Wish you were here!"
            },
            "created_at": "2023-10-01T12:05:00Z"
        }

        asyncio.run(process_create_postcard(meta, data))

        mock_add_item.assert_called_once_with(
            meta["token"],
            "postcard_entity",
            ENTITY_VERSION,
            {
                "postcard_id": "job_001",
                "user_id": "12345",
                "image_url": "https://example.com/image.jpg",
                "message": "Wish you were here!",
                "created_at": "2023-10-01T12:05:00Z",
                "status": "pending"
            }
        )

    @patch("app_init.app_init.entity_service.add_item")
    def test_process_send_postcard(self, mock_add_item):
        mock_add_item.return_value = "delivery_status_entity_id"

        meta = {"token": "test_token"}
        data = {
            "job_id": "job_001",
            "user_id": "12345",
            "request_parameters": {
                "recipient_name": "Jane Smith",
                "recipient_address": "123 Main St, Anytown, USA"
            },
            "created_at": "2023-10-01T12:05:00Z"
        }

        asyncio.run(process_send_postcard(meta, data))

        mock_add_item.assert_called_once_with(
            meta["token"],
            "delivery_status_entity",
            ENTITY_VERSION,
            {
                "delivery_status_id": "job_001",
                "postcard_id": "job_001",
                "status": "sent",
                "recipient": {
                    "name": "Jane Smith",
                    "address": "123 Main St, Anytown, USA",
                    "email": "unknown@example.com"
                },
                "sent_date": "2023-10-01T12:05:00Z",
                "estimated_delivery_date": "2023-10-05T15:00:00Z",
                "tracking_number": "TRKjob_001",
                "delivery_updates": [],
                "request_parameters": {
                    "postcard_id": "job_001",
                    "user_id": "12345",
                    "action": "send_postcard"
                }
            }
        )


if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation:
# 1. **process_create_postcard**: This function creates a postcard based on input data and saves it as a `postcard_entity`.
# 2. **process_send_postcard**: This function manages the sending of a postcard and saves the delivery status as a `delivery_status_entity`.
# 3. **Testing**: Unit tests with mocks for the `entity_service.add_item` function to ensure that the process functions behave correctly without needing actual service calls.
# 
# If you need any adjustments or further explanations, just let me know! 😊