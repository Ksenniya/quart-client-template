{
    "name": "job_workflow",
    "description": "Workflow for creating reports in processing state",
    "workflow_criteria": {
        "externalized_criteria": [],
        "condition_criteria": [
            {
                "name": "job",
                "description": "Workflow criteria",
                "condition": {
                    "group_condition_operator": "AND",
                    "conditions": [
                        {
                            "field_name": "entityModelName",
                            "is_meta_field": true,
                            "operation": "equals",
                            "value": "job",
                            "value_type": "strings"
                        },
                        {
                            "field_name": "entityModelVersion",
                            "is_meta_field": true,
                            "operation": "equals",
                            "value": "1000",
                            "value_type": "strings"
                        }
                    ]
                }
            }
        ]
    },
    "transitions": [
        {
            "name": "create_report",
            "description": "Create a report",
            "start_state": "None",
            "start_state_description": "Initial state",
            "end_state": "processing",
            "end_state_description": "Report is being processed",
            "automated": true,
            "transition_criteria": {
                "externalized_criteria": [],
                "condition_criteria": []
            },
            "processes": {
                "schedule_transition_processors": [],
                "externalized_processors": [
                    {
                        "name": "createReportProcessor",
                        "description": "Processor for creating a report",
                        "calculation_nodes_tags": "8b53241a-e8e0-11ef-9198-40c2ba0ac9eb",
                        "attach_entity": true,
                        "calculation_response_timeout_ms": "120000",
                        "retry_policy": "FIXED",
                        "sync_process": false,
                        "new_transaction_for_async": true,
                        "none_transactional_for_async": false,
                        "processor_criteria": {
                            "externalized_criteria": [],
                            "condition_criteria": []
                        }
                    }
                ]
            }
        }
    ]
}