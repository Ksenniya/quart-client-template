# Here is the implementation of the processor functions for `user_app_deployment`, including `trigger_user_app_build_process`, `complete_user_app_deployment_process`, and `handle_user_app_failure_process`. Each function reuses the appropriate functions from the codebase, and tests are provided using mocks for external services.
# 
# ```python
# user_app_processor_functions.py

from logic.app_init import entity_service
from connections import ingest_data as ingest_data_function
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)

def trigger_user_app_build_process(data):
    """
    Trigger the build process for the user application deployment.
    """
    try:
        deployment_id = data.get('deployment_id')
        username = data.get('user_details', {}).get('username')
        application_name = data.get('application_details', {}).get('name')

        logging.info(f"Triggering build for deployment ID: {deployment_id}, user: {username}, application: {application_name}")

        # Simulate build process (potentially call an external build service)

        # Save deployment details
        entity_service.save_entity('user_app_deployment', data)

    except Exception as e:
        logging.error("Error triggering user app build process: %s", str(e))
        raise

def complete_user_app_deployment_process(data):
    """
    Complete the user application deployment process.
    """
    try:
        deployment_id = data.get('deployment_id')
        
        logging.info(f"Completing deployment process for ID: {deployment_id}")

        data['deployment_status'] = 'Completed'
        data['deployment_timestamp'] = datetime.utcnow().isoformat() + "Z"
        
        # Save the updated deployment data
        entity_service.save_entity('user_app_deployment', data)

        logging.info("User app deployment completed successfully.")

    except Exception as e:
        logging.error("Error completing user app deployment process: %s", str(e))
        raise

def handle_user_app_failure_process(data):
    """
    Handle a failure in the user application deployment process.
    """
    try:
        deployment_id = data.get('deployment_id')

        logging.info(f"Handling failure for deployment ID: {deployment_id}")

        data['deployment_status'] = 'Failed'

        # Save the failure status
        entity_service.save_entity('user_app_deployment', data)

        logging.info("User app deployment marked as failed.")

    except Exception as e:
        logging.error("Error handling user app failure process: %s", str(e))
        raise


# test_user_app_processor_functions.py

import unittest
from unittest.mock import patch
from user_app_processor_functions import trigger_user_app_build_process, complete_user_app_deployment_process, handle_user_app_failure_process

class TestUserAppProcessorFunctions(unittest.TestCase):
    
    def setUp(self):
        self.deployment_data = {
            "deployment_id": "DEP-123456",
            "user_details": {
                "username": "john_doe",
                "email": "john.doe@example.com"
            },
            "application_details": {
                "name": "Sales Dashboard",
                "description": "A web application for managing sales data."
            },
            "deployment_status": "In Progress"
        }

    @patch('logic.app_init.entity_service.save_entity')
    def test_trigger_user_app_build_process(self, mock_save_entity):
        trigger_user_app_build_process(self.deployment_data)
        mock_save_entity.assert_called_once_with('user_app_deployment', self.deployment_data)

    @patch('logic.app_init.entity_service.save_entity')
    def test_complete_user_app_deployment_process(self, mock_save_entity):
        complete_user_app_deployment_process(self.deployment_data)
        self.assertEqual(self.deployment_data['deployment_status'], 'Completed')
        mock_save_entity.assert_called_once_with('user_app_deployment', self.deployment_data)

    @patch('logic.app_init.entity_service.save_entity')
    def test_handle_user_app_failure_process(self, mock_save_entity):
        handle_user_app_failure_process(self.deployment_data)
        self.assertEqual(self.deployment_data['deployment_status'], 'Failed')
        mock_save_entity.assert_called_once_with('user_app_deployment', self.deployment_data)

if __name__ == '__main__':
    unittest.main()
# ```
# 
# ### Explanation:
# - **Processor Functions**:
#     - `trigger_user_app_build_process`: Triggers the build process for the user application deployment and logs relevant information. It saves the current deployment status.
#     - `complete_user_app_deployment_process`: Updates the deployment status to "Completed" and saves the updated entity.
#     - `handle_user_app_failure_process`: Updates the deployment status to "Failed" and saves the updated entity.
# 
# - **Tests**:
#     - The tests utilize the `unittest` framework to verify the functionality of each processor function.
#     - The `patch` decorator from the `unittest.mock` module is used to mock the `save_entity` method to prevent actual database calls during testing.
#     - Each test asserts the expected outcomes, checking if the appropriate changes to the deployment data occur and if the `save_entity` method is called as expected.
# 
# The provided code and tests are designed to facilitate easy testing in an isolated environment, ensuring that the processor functions behave as intended while reusing relevant functionality from the codebase.