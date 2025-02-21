Below is an example of a refactored version of your entity/prototype.py file. In this version all local in‑memory storage is replaced by calls to the external service (entity_service). The POST /job endpoint now calls entity_service.add_item to create a “report” record and returns its id for further queries. In the background task process_report the report is updated via entity_service.update_item. Likewise, GET /report/<job_id> now retrieves the report via entity_service.get_item. The original business logic (fetching BTC rates, sending an email, etc.) is preserved. Also added is the startup routine to initialize cyoda. (Note: if any of the external calls do not offer full functionality compared to the local cache then the “if this is not enough just skip and leave as is” instruction was followed by leaving some business logic intact.) 

Below is the refactored file:

------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
from datetime import datetime

from dataclasses import dataclass
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response  # validate_querystring available if needed
import aiohttp

# Import external service and constants
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Register QuartSchema

# Remove local in‑memory cache in favor of external entity_service.
# REPORTS = {}   <-- no longer used


@dataclass
class JobRequest:
    recipient_email: str  # Primitive type: string


@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)


async def process_report(report_id: str, recipient_email: str):
    """
    Asynchronous task to fetch BTC conversion rates from an external API,
    send an email (placeholder) and update the report via entity_service.
    """
    rates = {}
    try:
        async with aiohttp.ClientSession() as session:
            # TODO: Replace the URL with a valid BTC conversion rates API endpoint.
            async with session.get("https://api.example.com/btc_rates") as response:
                if response.status == 200:
                    data = await response.json()
                    rates["BTC_USD"] = data.get("BTC_USD", 0.0)
                    rates["BTC_EUR"] = data.get("BTC_EUR", 0.0)
                else:
                    # TODO: Implement proper error handling or logging for non-200 response statuses.
                    rates = {"BTC_USD": 0.0, "BTC_EUR": 0.0}
    except Exception as e:
        # TODO: Implement proper exception logging.
        print(f"Error fetching BTC rates: {e}")
        rates = {"BTC_USD": 0.0, "BTC_EUR": 0.0}

    # Simulate sending an email report (placeholder).
    await asyncio.sleep(0.1)  # simulate delay
    print(f"Sending email report to {recipient_email} with rates: {rates}")

    # Prepare the update payload with additional fields.
    update_data = {
        "report_id": report_id,
        "status": "completed",
        "completedAt": datetime.utcnow().isoformat() + "Z",
        "rates": rates,
        "recipient_email": recipient_email
    }
    # Update the report using the external service.
    entity_service.update_item(
        token=cyoda_token,
        entity_model="report",
        entity_version=ENTITY_VERSION,
        entity=update_data,
        meta={}
    )


@app.route("/job", methods=["POST"])
@validate_request(JobRequest)  # For POST endpoints, place validation after the route decorator.
@validate_response(dict, 202)    # For POST endpoints, response validation follows.
async def job(data: JobRequest):
    """
    POST /job
    Initiates the report creation process.
    Business Logic:
      - Fetch BTC/USD and BTC/EUR conversion rates via an external API.
      - Store the report in an external service via entity_service.
      - Trigger an email send (placeholder).
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
    requested_at = datetime.utcnow().isoformat() + "Z"

    # Prepare the initial report payload.
    report_data = {
        "status": "processing",
        "requestedAt": requested_at,
        "recipient_email": recipient_email
    }
    # Add the report record via the external service; the id returned is used for future queries.
    report_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="report",
        entity_version=ENTITY_VERSION,
        entity=report_data
    )

    # Fire-and-forget the processing task.
    asyncio.create_task(process_report(report_id, recipient_email))

    # Immediately return a response indicating that the report is processing.
    response = {
        "report_id": report_id,
        "status": "processing",
        "rates": None  # Will be populated once processing is complete.
    }
    return jsonify(response), 202


@app.route("/report/<report_id>", methods=["GET"])
async def get_report(report_id: str):
    """
    GET /report/<report_id>
    Retrieves a stored report by its report identifier.
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
    # Retrieve the report via the external service.
    report = entity_service.get_item(
        token=cyoda_token,
        entity_model="report",
        entity_version=ENTITY_VERSION,
        technical_id=report_id
    )
    if not report:
        abort(404, description=f"Report with id {report_id} not found.")
    return jsonify(report)


if __name__ == '__main__':
    # Start the application with the specified entry point settings.
    # Note: The threaded option is preserved from the original code.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

------------------------------------------------

Key changes made:
1. Removed local REPORTS dict and replaced storage calls with entity_service.add_item, get_item, and update_item.
2. The POST /job route creates a report via entity_service and schedules process_report.
3. The process_report task updates the report record using entity_service.update_item.
4. The GET /report/<report_id> endpoint retrieves the report from the external service.
5. Added the startup routine (using init_cyoda) before serving requests.
6. All calls to the external service consistently use ENTITY_VERSION and the provided cyoda_token.

This refactoring preserves the main business functionality (data ingestion, external API calls, email simulation, etc.) while replacing in‑memory caching with external service calls.