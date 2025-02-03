# Here’s the implementation of the processor functions for the `greeting_entity`, specifically for the functions `generate_greeting` and `show_greeting`. The code will include logic to save the greeting entity and will feature unit tests with mocks for external services or functions.
# 
# ```python
import logging
import json
from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_greeting(meta, data):
    """Generate a personalized greeting message based on user input."""
    try:
        user_name = data.get("input_name", "Guest")
        greeting_message = f"Hello, {user_name}!"

        # Create greeting entity data
        greeting_entity_data = {
            "greeting_id": data.get("greeting_id"),
            "user_id": data.get("user_id"),
            "message": greeting_message,
            "timestamp": data.get("request_time"),
        }

        # Save the greeting entity
        greeting_entity_id = await entity_service.add_item(
            meta["token"], "greeting_entity", ENTITY_VERSION, greeting_entity_data
        )

        data["greeting_entity"] = {"technical_id": greeting_entity_id}
        logger.info(f"Greeting generated successfully: {greeting_message}")

    except Exception as e:
        logger.error(f"Error in generate_greeting: {e}")
        raise


async def show_greeting(meta, data):
    """Show the personalized greeting to the user."""
    try:
        greeting_entity = data.get("greeting_entity", {})
        if greeting_entity:
            greeting_message = f"Greeting: {greeting_entity.get('message', 'No greeting found')}"
            logger.info(greeting_message)
            return greeting_message
        else:
            logger.warning("No greeting entity found.")
            return "No greeting available."
    except Exception as e:
        logger.error(f"Error in show_greeting: {e}")
        raise


# Unit tests
class TestGreetingEntityProcessorFunctions(IsolatedAsyncioTestCase):

    @patch("app_init.app_init.entity_service.add_item")
    def test_generate_greeting(self, mock_add_item):
        mock_add_item.return_value = "greeting_entity_id"
        
        meta = {"token": "test_token"}
        data = {
            "input_name": "John",
            "greeting_id": "abc123",
            "user_id": "user001",
            "request_time": "2023-10-01T12:00:00Z"
        }

        async def run_test():
            await generate_greeting(meta, data)
            self.assertEqual(data["greeting_entity"]["technical_id"], "greeting_entity_id")
        
        self.loop.run_until_complete(run_test())

    @patch("builtins.print")
    def test_show_greeting(self, mock_print):
        data = {
            "greeting_entity": {
                "message": "Hello, John!"
            }
        }

        async def run_test():
            message = await show_greeting({"token": "test_token"}, data)
            self.assertEqual(message, "Greeting: Hello, John!")

        self.loop.run_until_complete(run_test())


if __name__ == '__main__':
    import unittest
    unittest.main()
# ```
# 
# ### Explanation of the Code
# 
# 1. **generate_greeting**:
#    - Generates a personalized greeting based on user input.
#    - Constructs a greeting message and saves the `greeting_entity` using `entity_service.add_item`.
#    - Updates `data` with the technical ID of the newly created greeting entity.
# 
# 2. **show_greeting**:
#    - Retrieves the greeting message from `data` and logs it for display.
#    - Returns a message to inform the user.
# 
# 3. **Unit Tests**:
#    - Tests are provided for both functions using `unittest`.
#    - Mocks are used to simulate external service calls and validate functionality.
# 
# Feel free to tweak any part of this code or let me know if you need further modifications!