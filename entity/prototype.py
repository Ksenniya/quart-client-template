#!/usr/bin/env python3
import asyncio
import uuid
from datetime import datetime

from dataclasses import dataclass
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response  # validate_querystring available if needed
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # Register QuartSchema

# In-memory persistence mock for reports/jobs.
REPORTS = {}


@dataclass
class JobRequest:
    recipient_email: str  # Primitive type: string


# Note: Due to issues with quart-schema validations order on GET vs POST,
# for POST endpoints, the route decorator is first, followed by validation decorators.
# For GET endpoints, if query string validation is needed, it must be placed first.
# In our case, GET /report/<job_id> does not use request body or querystring validation.


async def process_report(job_id: str, recipient_email: str):
    """
    Asynchronous task to fetch BTC conversion rates from an external API,
    send an email (placeholder) and update the report.
    """
    # TODO: Replace the placeholder rates with a proper external API call.
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

    # TODO: Handle any additional calculations if necessary.

    # Simulate sending an email report (placeholder).
    await asyncio.sleep(0.1)  # simulate delay
    print(f"Sending email report to {recipient_email} with rates: {rates}")
    # TODO: Replace print with actual email sending logic (SMTP, SendGrid, etc.)

    # Update the report with completion details.
    REPORTS[job_id].update({
        "status": "completed",
        "completedAt": datetime.utcnow().isoformat() + "Z",
        "rates": rates
    })


@app.route("/job", methods=["POST"])
@validate_request(JobRequest)  # Workaround: For POST endpoints, place validation after route decorator.
@validate_response(dict, 202)    # Workaround: For POST endpoints, response validation follows.
async def job(data: JobRequest):
    """
    POST /job
    Initiates the report creation process.
    Business Logic:
      - Fetch BTC/USD and BTC/EUR conversion rates via an external API.
      - Store the job/report in an in-memory store.
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
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"

    # Save the initial report state in our in-memory persistence.
    REPORTS[job_id] = {
        "report_id": job_id,
        "status": "processing",
        "requestedAt": requested_at,
        "recipient_email": recipient_email
    }

    # Fire-and-forget the processing task.
    asyncio.create_task(process_report(job_id, recipient_email))

    # Immediately return a response indicating that the report is processing.
    response = {
        "report_id": job_id,
        "status": "processing",
        "rates": None  # Will be populated once processing is complete.
    }
    return jsonify(response), 202


@app.route("/report/<job_id>", methods=["GET"])
async def get_report(job_id: str):
    """
    GET /report/<job_id>
    Retrieves a stored report by its job/report identifier.
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
    report = REPORTS.get(job_id)
    if not report:
        abort(404, description=f"Report with id {job_id} not found.")
    return jsonify(report)


if __name__ == '__main__':
    # Start the application with the specified entry point settings.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

"""
Mermaid Sequence Diagram:

    sequenceDiagram
        participant U as User
        participant A as Application
        participant E as External API
        participant M as Email Service

        U->>A: POST /job { recipient_email }
        A->>E: Request BTC conversion rates (via aiohttp)
        E-->>A: Return conversion rates (placeholder)
        A->>A: Store report in local cache; Fire process_report task
        A->>M: Simulated email send (print statement)
        M-->>A: Email send confirmation (simulated)
        A-->>U: Response with report_id, status ("processing")

        U->>A: GET /report/<job_id>
        A->>A: Retrieve stored report from local cache
        A-->>U: Return report, including conversion rate details (if completed)
        
Note: The placement of @validate_request and @validate_response decorators for POST endpoints follows a workaround due to current issues in the quart-schema library.
"""