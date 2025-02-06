# Below is the implementation of the `save_user` processor function along with tests using mocks for external services or functions. The function reuses existing logic, particularly for data ingestion, and ensures any necessary dependencies are handled.
# 
# ```python
import asyncio
import logging
from logic.app_init import entity_service
from connections import ingest_data as ingest_user_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def save_user(meta, user_data):
    """
    Save a new user and generate a Bearer token.
    
    :param meta: Metadata related to the request
    :param user_data: Data of the user entity
    :return: User details and Bearer token
    """
    try:
        # Validate user data (basic validation logic can be implemented)
        if not user_data.get("username") or not user_data.get("email"):
            raise ValueError("Username and email are required")

        # Ingest user data, if required (this should use the existing ingest_data function)
        raw_request_id = await ingest_user_data(user_data)

        # Save user entity to Cyoda
        user = await entity_service.add("user", user_data)

        # Here you could save the raw_request_id to a corresponding raw data entity if needed
        
        # Generate Bearer token for the user (token generation logic to be implemented)
        token = generate_token(user)  # Assume a token generation function exists

        return {
            "user_details": user,
            "token": token,
            "raw_request_id": raw_request_id  # Return raw_request_id for tracking
        }
    except Exception as e:
        logger.error(f"Error saving user: {e}")
        raise

# Example token generation function (stub for illustration)
def generate_token(user):
    # Logic for generating a token for the user
    return "Bearer token..."

# Unit Test for save_user
import unittest
from unittest.mock import patch, AsyncMock

class TestSaveUser(unittest.TestCase):
    @patch('logic.app_init.entity_service')
    @patch('connections.ingest_data')
    def test_save_user(self, mock_ingest_data, mock_entity_service):
        mock_ingest_data.return_value = AsyncMock(return_value='raw_data_id')
        mock_entity_service.add.return_value = AsyncMock(return_value={'user_id': '12345', 'username': 'test_user'})

        user_data = {
            "username": "test_user",
            "email": "test_user@example.com",
            "password": "securepassword123"
        }
        
        meta = {}

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(save_user(meta, user_data))

        self.assertEqual(result["user_details"]["username"], "test_user")
        self.assertEqual(result["token"], "Bearer token...")
        self.assertEqual(result["raw_request_id"], 'raw_data_id')

    def test_save_user_validation(self):
        with self.assertRaises(ValueError):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(save_user({}, {"username": "", "email": "test_user@example.com"}))

if __name__ == '__main__':
    unittest.main()
# ```
# 
# ### Explanation
# - The `save_user` function validates input, ingests the user data using the existing `ingest_data` function, saves the user via the `entity_service`, and generates a token.
# - The test case mocks the external service calls to isolate the function for unit testing. It verifies that the expected user data is returned and checks for validation errors.
# - The `generate_token` function is a placeholder for actual token generation logic.
# 
# Feel free to ask if you need further modifications or explanations!