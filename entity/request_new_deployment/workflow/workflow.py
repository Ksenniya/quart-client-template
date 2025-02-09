# Here’s an implementation of the processor functions for `request_new_deployment`, including `initiate_deployment_process`, `complete_deployment_process`, and `cancel_deployment_process`. Each function makes use of existing utility functions in the codebase while ensuring that dependent entities are saved accordingly. Additionally, I've included tests with mocks for external services.
# 
# ```python
import json
import logging
import os
from unittest import TestCase, mock

from app_init.app_init import entity_service, ai_service
from common.service.connections import ingest_data as ingest_raw_data
from common.service.trino_service import get_trino_schema_id_by_entity_name

logger = logging.getLogger(__name__)

async def initiate_deployment_process(meta, data):
    """
    Initiates the deployment process for a new environment.
    """
    try:
        # Step 1: Validate the request data
        deployment_data = data.get('request_new_deployment')
        if not deployment_data:
            raise ValueError("No deployment data provided.")

        # Step 2: Call the entity service to initiate the deployment
        deployment_id = deployment_data.get('deployment_id')
        application_name = deployment_data.get('application_name')
        version = deployment_data.get('version')
        environment = deployment_data.get('environment')

        # Save the deployment to the entity service
        await entity_service.add_item(meta["token"], "request_new_deployment", "1.0", deployment_data)

        # Step 3: Ingest data if necessary
        if "raw_data" in deployment_data:
            raw_data_entity = await ingest_raw_data(meta["token"], deployment_data["raw_data"])
            logger.info(f"Ingested raw data entity: {raw_data_entity}")

        logger.info(f"Deployment initiated successfully for ID: {deployment_id}")

        return {"deployment_id": deployment_id, "status": "initiated"}

    except Exception as e:
        logger.error(f"Error initiating deployment: {e}")
        raise

async def complete_deployment_process(meta, data):
    """
    Completes the deployment process.
    """
    try:
        deployment_id = data["request_new_deployment"]["deployment_id"]

        # Fetch the existing deployment
        deployment = await entity_service.get_item(meta["token"], "request_new_deployment", "1.0", deployment_id)
        
        # Update the status to completed
        deployment["status"] = "completed"
        await entity_service.update_item(meta["token"], "request_new_deployment", "1.0", deployment_id, deployment, None)

        logger.info(f"Deployment completed successfully for ID: {deployment_id}")
        return {"deployment_id": deployment_id, "status": "completed"}

    except Exception as e:
        logger.error(f"Error completing deployment: {e}")
        raise

async def cancel_deployment_process(meta, data):
    """
    Cancels an ongoing deployment process.
    """
    try:
        deployment_id = data["request_new_deployment"]["deployment_id"]

        # Fetch the existing deployment
        deployment = await entity_service.get_item(meta["token"], "request_new_deployment", "1.0", deployment_id)

        # Update the status to canceled
        deployment["status"] = "canceled"
        await entity_service.update_item(meta["token"], "request_new_deployment", "1.0", deployment_id, deployment, None)

        logger.info(f"Deployment canceled successfully for ID: {deployment_id}")
        return {"deployment_id": deployment_id, "status": "canceled"}

    except Exception as e:
        logger.error(f"Error canceling deployment: {e}")
        raise

# Test cases for the processor functions
class TestRequestNewDeployment(TestCase):

    @mock.patch('app_init.app_init.entity_service.add_item')
    @mock.patch('app_init.app_init.entity_service.get_item')
    @mock.patch('app_init.app_init.entity_service.update_item')
    @mock.patch('common.service.connections.ingest_data')
    async def test_initiate_deployment_process(self, mock_ingest_data, mock_update_item, mock_get_item, mock_add_item):
        mock_add_item.return_value = {"deployment_id": "deployment-12345"}
        mock_ingest_data.return_value = {"raw_data_id": "raw_data_001"}

        meta = {"token": "test_token"}
        data = {
            "request_new_deployment": {
                "deployment_id": "deployment-12345",
                "application_name": "MyWebApp",
                "version": "1.0.0",
                "environment": "production",
                "raw_data": {"url": "http://example.com/data.csv"}
            }
        }

        result = await initiate_deployment_process(meta, data)
        
        self.assertEqual(result["deployment_id"], "deployment-12345")
        self.assertEqual(result["status"], "initiated")
        mock_add_item.assert_called_once()
        mock_ingest_data.assert_called_once()

    @mock.patch('app_init.app_init.entity_service.get_item')
    @mock.patch('app_init.app_init.entity_service.update_item')
    async def test_complete_deployment_process(self, mock_update_item, mock_get_item):
        mock_get_item.return_value = {
            "deployment_id": "deployment-12345",
            "status": "in_progress"
        }

        meta = {"token": "test_token"}
        data = {
            "request_new_deployment": {
                "deployment_id": "deployment-12345"
            }
        }

        result = await complete_deployment_process(meta, data)

        self.assertEqual(result["deployment_id"], "deployment-12345")
        self.assertEqual(result["status"], "completed")
        mock_update_item.assert_called_once()

    @mock.patch('app_init.app_init.entity_service.get_item')
    @mock.patch('app_init.app_init.entity_service.update_item')
    async def test_cancel_deployment_process(self, mock_update_item, mock_get_item):
        mock_get_item.return_value = {
            "deployment_id": "deployment-12345",
            "status": "in_progress"
        }

        meta = {"token": "test_token"}
        data = {
            "request_new_deployment": {
                "deployment_id": "deployment-12345"
            }
        }

        result = await cancel_deployment_process(meta, data)

        self.assertEqual(result["deployment_id"], "deployment-12345")
        self.assertEqual(result["status"], "canceled")
        mock_update_item.assert_called_once()


if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation:
# - **Processor Functions**:
#   - Each function (`initiate_deployment_process`, `complete_deployment_process`, `cancel_deployment_process`) follows a similar structure.
#   - They handle the respective processes of initiating, completing, or canceling a deployment based on the provided `data`.
#   - They utilize the `entity_service` for adding, getting, and updating deployment statuses.
#   - If necessary, they integrate the `ingest_data` function to handle data ingestion.
# 
# - **Testing**:
#   - Tests are integrated into the same file for convenience.
#   - They use mocks for external services to isolate the tests and provide a controlled environment.
#   - Each test checks the expected outcomes and ensures the corresponding functions are called.
# 
# Feel free to modify the test cases based on your specific requirements or additional suggestions!