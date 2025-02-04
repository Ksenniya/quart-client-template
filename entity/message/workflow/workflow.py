# Here’s the implementation of the processor functions for the `message` entity with the required public functions `save_message` and `display_message`. I've also included unit tests with mocks for external services to allow for testing in an isolated environment.
# 
# ```python
import logging
import json
import asyncio
from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def save_message(meta, data):
    """Processor function to save the Hello, World! message."""
    logger.info("Starting to save message.")
    try:
        # Simulating the saving of message data.
        message_data = {
            "id": data["id"],
            "text": data["text"],
            "timestamp": data["timestamp"]
        }

        # Save the message entity
        message_entity_id = await entity_service.add_item(
            meta["token"],
            "message",
            ENTITY_VERSION,
            message_data
        )

        logger.info(f"Message saved successfully with ID: {message_entity_id}")
        return message_entity_id
    except Exception as e:
        logger.error(f"Error in save_message: {e}")
        raise

async def display_message(meta, data):
    """Processor function to display the Hello, World! message."""
    logger.info("Starting to display message.")
    try:
        # Here, the 'data' would include the ID to retrieve the message
        message_id = data["id"]
        message = await entity_service.get_item(
            meta["token"],
            "message",
            ENTITY_VERSION,
            message_id
        )

        logger.info(f"Displaying message: {message['text']}")
        return message["text"]
    except Exception as e:
        logger.error(f"Error in display_message: {e}")
        raise

# Unit Tests
import unittest
from unittest.mock import patch

class TestMessageProcessors(unittest.TestCase):

    @patch("app_init.app_init.entity_service.add_item")
    async def test_save_message(self, mock_add_item):
        mock_add_item.return_value = "message_entity_id"

        meta = {"token": "test_token"}
        data = {
            "id": 1,
            "text": "Hello, World!",
            "timestamp": "2023-10-03T12:00:00Z"
        }

        result = await save_message(meta, data)
        
        mock_add_item.assert_called_once_with(
            meta["token"],
            "message",
            ENTITY_VERSION,
            {
                "id": 1,
                "text": "Hello, World!",
                "timestamp": "2023-10-03T12:00:00Z"
            }
        )
        self.assertEqual(result, "message_entity_id")

    @patch("app_init.app_init.entity_service.get_item")
    async def test_display_message(self, mock_get_item):
        mock_get_item.return_value = {"text": "Hello, World!"}

        meta = {"token": "test_token"}
        data = {"id": "message_entity_id"}

        result = await display_message(meta, data)

        mock_get_item.assert_called_once_with(
            meta["token"],
            "message",
            ENTITY_VERSION,
            "message_entity_id"
        )
        self.assertEqual(result, "Hello, World!")

if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation
# - **`save_message` function**: This function saves the "Hello, World!" message using the `entity_service.add_item` method. It accepts `meta` and `data` as parameters and handles logging.
# - **`display_message` function**: This function displays the message by retrieving it from the entity service using `entity_service.get_item`.
# - **Unit Tests**: Tests for both processor functions are included. Mocks for `entity_service` functions allow for isolated testing without relying on actual service implementations.
# 
# Feel free to modify or expand on any part of this implementation! If you have further questions or suggestions, just let me know!