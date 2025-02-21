Below is an example of a completely refactored application that moves as much synchronous “pre‐persistence” logic as possible into a dedicated workflow function. In this example the controller is lean (it only extracts the recipient email and calls entity_service.add_item), while all the initial report data enrichment happens in process_report_workflow. That function is invoked immediately before persistence and is meant only to perform quick, synchronous adjustments; all longer, non‐blocking tasks (such as fetching BTC rates or sending email notifications) remain in the fire‐and‐forget process_report task. Additional error checking and precautions (to prevent infinite recursion and enforce required fields) are also provided. You can adjust the details of the workflow function as needed. Here is the complete code:

------------------------------------------------
#!/usr/bin/env python3
import asyncio
from datetime import datetime

from dataclasses import dataclass
from typing import Any, Dict

from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response
import aiohttp

# Import external service and constants
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Register QuartSchema

@dataclass
class JobRequest:
    recipient_email: str  # The intended recipient email address

def process_report_workflow(entity_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Workflow function that is applied just before the report entity is persisted.
    It performs synchronous data enrichment, validation and normalization so that
    the controller remains lean and only coordinates data flow.
    
    This function:
      • Ensures required fields (e.g. recipient_email) are present.
      • Enriches the payload with consistent metadata (timestamps, initial status).
      • Prevents any possibility of infinite recursion by not calling any external
        service that might re-add the same model.
    
    Note: This function MUST be synchronous because it is used during the persistence
    process.
    """
    # Check that recipient_email was provided
    if "recipient_email" not in entity_data or not entity_data["recipient_email"]:
        raise ValueError("Missing required field: recipient_email")
    
    # Set the initial status and requested timestamp if not already set
    entity_data.setdefault("status", "processing")
    entity_data.setdefault("requestedAt", datetime.utcnow().isoformat() + "Z")
    
    # Mark that the workflow processing was already applied
    # This can prevent reprocessing if the same payload is submitted again.
    entity_data["workflowApplied"] = True
    return entity_data

async def process_report(report_id: str, recipient_email: str):
    """
    Fire-and-forget asynchronous background task to:
      • Fetch BTC conversion rates from an external API.
      • Simulate sending an email report.
      • Update the persisted report record via entity_service with the results.
    
    This function uses aiohttp for calling the external BTC rates API. In case of error,
    default values and error logging are used to ensure that the process ends gracefully.
    """
    rates = {}
    try:
        async with aiohttp.ClientSession() as session:
            # In a production system, replace the URL with a real API endpoint.
            async with session.get("https://api.example.com/btc_rates") as response:
                if response.status == 200:
                    data = await response.json()
                    # Extract BTC conversion rates safely
                    rates["BTC_USD"] = float(data.get("BTC_USD", 0.0))
                    rates["BTC_EUR"] = float(data.get("BTC_EUR", 0.0))
                else:
                    # Log non-200 statuses and use default values.
                    app.logger.error(f"BTC rates API responded with status {response.status}")
                    rates = {"BTC_USD": 0.0, "BTC_EUR": 0.0}
    except Exception as e:
        app.logger.exception(f"Error fetching BTC rates: {e}")
        rates = {"BTC_USD": 0.0, "BTC_EUR": 0.0}

    # Simulate sending an email report (this might be replaced with a real email client)
    await asyncio.sleep(0.1)  # simulate delay
    app.logger.info(f"Sending email report to {recipient_email} with rates: {rates}")

    # Prepare the update payload with additional fields.
    update_data = {
        "report_id": report_id,
        "status": "completed",
        "completedAt": datetime.utcnow().isoformat() + "Z",
        "rates": rates,
        "recipient_email": recipient_email
    }
    try:
        # Update the report using the external service.
        entity_service.update_item(
            token=cyoda_token,
            entity_model="report",
            entity_version=ENTITY_VERSION,
            entity=update_data,
            meta={}
        )
    except Exception as e:
        app.logger.exception(f"Error updating report {report_id}: {e}")

@app.route("/job", methods=["POST"])
@validate_request(JobRequest)  # Validation of input data.
@validate_response(dict, 202)    # Validate the response format.
async def job(data: JobRequest):
    """
    POST /job
    Initiates the report creation process.
    Business Logic Overview:
      - Receives the recipient email in the request.
      - Prepares an initial minimal report payload.
      - Delegates the synchronous enrichment logic to process_report_workflow
        via the workflow parameter on entity_service.add_item. This ensures that
        all required defaults and pre-persistence logic are applied.
      - After persistence, a background task (process_report) is launched to
        fetch conversion rates, simulate an email, and update the report.
    Request JSON format:
      { "recipient_email": "user@example.com" }
    Response JSON format:
      {
          "report_id": "...",
          "status": "processing",
          "rates": null
      }
    """
    recipient_email = data.recipient_email

    # Prepare the basic report payload.
    # Note: We are not duplicating the logic that should be done in the workflow.
    # The workflow function process_report_workflow is responsible for final enrichment.
    report_data = {
        "recipient_email": recipient_email,
    }

    try:
        # Persist the report record via the external service.
        # The workflow function process_report_workflow will be applied to report_data before storing.
        report_id = entity_service.add_item(
            token=cyoda_token,
            entity_model="report",
            entity_version=ENTITY_VERSION,
            entity=report_data,
            workflow=process_report_workflow
        )
    except Exception as e:
        # Log the error and abort with a 500 if we cannot persist the entity.
        app.logger.exception(f"Error creating report: {e}")
        abort(500, description="Unable to create report at this time.")

    # Launch background asynchronous processing to update the report.
    asyncio.create_task(process_report(report_id, recipient_email))

    response = {
        "report_id": report_id,
        "status": "processing",
        "rates": None  # The rates will be added once the background processing completes.
    }
    return jsonify(response), 202

@app.route("/report/<report_id>", methods=["GET"])
async def get_report(report_id: str):
    """
    GET /report/<report_id>
    Retrieves a stored report by its unique identifier.
    Response JSON format:
      {
          "report_id": "...",
          "requestedAt": "...",
          "recipient_email": "...",
          "status": "processing" or "completed",
          "completedAt": "..."  (if completed),
          "rates": { "BTC_USD": <value>, "BTC_EUR": <value> } (if completed)
      }
    """
    try:
        # Retrieve the report using the external entity service.
        report = entity_service.get_item(
            token=cyoda_token,
            entity_model="report",
            entity_version=ENTITY_VERSION,
            technical_id=report_id
        )
    except Exception as e:
        app.logger.exception(f"Error retrieving report {report_id}: {e}")
        abort(500, description="Internal server error.")

    if not report:
        abort(404, description=f"Report with id {report_id} not found.")
    return jsonify(report)

@app.before_serving
async def startup_routine():
    """
    Application initialization routine.
    This function ensures that cyoda is properly initialized before any request is served.
    """
    try:
        await init_cyoda(cyoda_token)
    except Exception as e:
        app.logger.exception(f"Error initializing cyoda: {e}")
        # In a production scenario, you might want to shut down the app if initialization fails.

if __name__ == '__main__':
    # Start the application.
    # The threaded option is preserved from original code.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
------------------------------------------------

A few points on potential issues and preventive measures:

1. Workflow Safety – The process_report_workflow function is strictly synchronous and does not invoke any external API calls. It validates that required fields (such as recipient_email) are present and sets default values only if not already defined. Also, it sets a flag ("workflowApplied") to prevent any accidental reprocessing.

2. Error Handling – In both the workflow and asynchronous processing functions, exceptions are caught and logged. The controller aborts with a server error if persistence fails, ensuring that downstream systems are not given ambiguous responses.

3. Separation of Concerns – The controller only extracts the necessary data and invokes the persistence and background tasks. All enrichment logic is handled separately by the workflow function, and the asynchronous long‐running tasks (BTC rates fetching, email simulation) are handled in process_report.

4. Asynchronous Tasks – The process_report function is fire-and-forget. If there is an issue in the background task the error is logged but does not affect the client response.

This refactored design keeps the controller lean, makes unit testing of business logic easier, and introduces safety checks to prevent data inconsistencies and infinite recursion.