# Below is the implementation of the processor functions `save_deployment`, `fetch_deployment_status`, and `cancel_deployment`, along with tests using mocks for external services or functions. The functions utilize existing logic and ensure dependencies are managed correctly.
# 
# ```python
import asyncio
import logging
from logic.app_init import entity_service
from connections import ingest_data as ingest_deployment_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def save_deployment(meta, deployment_data):
    """
    Save a new deployment.
    
    :param meta: Metadata related to the request
    :param deployment_data: Data of the deployment entity
    :return: Deployment details
    """
    try:
        # Validate deployment data
        if not deployment_data.get("repository_url") or not deployment_data.get("environment_id"):
            raise ValueError("Repository URL and Environment ID are required")

        # Ingest deployment data, if required
        raw_request_id = await ingest_deployment_data(deployment_data)

        # Save deployment entity to Cyoda
        deployment = await entity_service.add("deployment", deployment_data)

        # Optional: Save raw_request_id to a corresponding raw data entity if needed
        
        return {
            "deployment_details": deployment,
            "raw_request_id": raw_request_id  # Returning raw_request_id for tracking
        }
    except Exception as e:
        logger.error(f"Error saving deployment: {e}")
        raise

async def fetch_deployment_status(meta, deployment_id):
    """
    Fetch the current status of a deployment.
    
    :param meta: Metadata related to the request
    :param deployment_id: ID of the deployment to fetch status for
    :return: Deployment status
    """
    try:
        # Fetch deployment entity details from Cyoda
        deployment = await entity_service.get("deployment", deployment_id)

        # Simulate fetching current status from TeamCity (assumed function)
        status = await get_status_from_teamcity(deployment.teamcity_build_id)

        return {
            "deployment_id": deployment_id,
            "status": status
        }
    except Exception as e:
        logger.error(f"Error fetching deployment status: {e}")
        raise

async def cancel_deployment(meta, deployment_id):
    """
    Cancel an ongoing deployment.
    
    :param meta: Metadata related to the request
    :param deployment_id: ID of the deployment to cancel
    :return: Cancellation confirmation
    """
    try:
        # Fetch deployment details to be canceled
        deployment = await entity_service.get("deployment", deployment_id)

        if deployment.status != "queued":
            raise ValueError("Deployment is not in a cancellable state")
        
        # Trigger cancellation in TeamCity (assumed function)
        await cancel_teamcity_build(deployment.teamcity_build_id)

        return {
            "deployment_id": deployment_id,
            "status": "cancellation requested"
        }
    except Exception as e:
        logger.error(f"Error cancelling deployment: {e}")
        raise

# Unit Test for deployment processors
import unittest
from unittest.mock import patch, AsyncMock

class TestDeploymentProcessors(unittest.TestCase):
    @patch('logic.app_init.entity_service')
    @patch('connections.ingest_data')
    async def test_save_deployment(self, mock_ingest_data, mock_entity_service):
        mock_ingest_data.return_value = AsyncMock(return_value='raw_data_id')
        mock_entity_service.add.return_value = AsyncMock(return_value={'deployment_id': 'deploy_001', 'repository_url': 'http://repository.url/myapp'})

        deployment_data = {
            "repository_url": "http://repository.url/myapp",
            "environment_id": "env_001",
            "is_public": True
        }
        
        meta = {}

        loop = asyncio.get_event_loop()
        result = await save_deployment(meta, deployment_data)

        self.assertEqual(result["deployment_details"]["repository_url"], "http://repository.url/myapp")
        self.assertEqual(result["raw_request_id"], 'raw_data_id')

    @patch('logic.app_init.entity_service')
    async def test_fetch_deployment_status(self, mock_entity_service):
        mock_entity_service.get.return_value = AsyncMock(return_value={'deployment_id': 'deploy_001', 'teamcity_build_id': 'build_67890'})
        # Assuming a function to mock TeamCity status fetching
        mock_get_status_from_teamcity.return_value = 'in_progress'

        deployment_id = "deploy_001"
        meta = {}

        loop = asyncio.get_event_loop()
        result = await fetch_deployment_status(meta, deployment_id)

        self.assertEqual(result["deployment_id"], deployment_id)
        self.assertEqual(result["status"], 'in_progress')

    @patch('logic.app_init.entity_service')
    async def test_cancel_deployment(self, mock_entity_service):
        mock_entity_service.get.return_value = AsyncMock(return_value={'deployment_id': 'deploy_001', 'status': 'queued'})
        # Assuming a function to mock cancellation in TeamCity
        mock_cancel_teamcity_build.return_value = None

        deployment_id = "deploy_001"
        meta = {}

        loop = asyncio.get_event_loop()
        result = await cancel_deployment(meta, deployment_id)

        self.assertEqual(result["deployment_id"], deployment_id)
        self.assertEqual(result["status"], "cancellation requested")

    def test_save_deployment_validation(self):
        with self.assertRaises(ValueError):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(save_deployment({}, {"repository_url": "", "environment_id": ""}))

    def test_cancel_deployment_validation(self):
        with self.assertRaises(ValueError):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(cancel_deployment({}, "invalid_deployment_id"))

if __name__ == '__main__':
    unittest.main()
# ```
# 
# ### Explanation
# - **Processor Functions**: 
#   - `save_deployment`: Validates deployment data, ingests it using the existing `ingest_data` function, and saves the deployment entity.
#   - `fetch_deployment_status`: Fetches the current deployment status from Cyoda and simulates integration with TeamCity.
#   - `cancel_deployment`: Cancels an ongoing deployment based on its current status.
# 
# - **Testing**: 
#   - Unit tests mock the `entity_service` and `ingest_data` to isolate each function for testing.
#   - The tests validate functionality and ensure proper error handling when required fields are missing.
# 
# This ensures the functions can be independently verified without external dependencies and reinforces the reuse of existing ingestion logic. If you have further questions or need adjustments, feel free to ask!