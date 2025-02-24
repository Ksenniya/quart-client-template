#!/usr/bin/env python3
import asyncio
import uuid
import datetime
import json
import aiohttp

from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring

# Import external services/configs
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

# Use a constant for the entity model name.
ENTITY_MODEL = "report"

# Data classes for request/response models
@dataclass
class JobRequest:
    # No payload required for job creation; placeholder for validation.
    pass

@dataclass
class JobResponse:
    report_id: str
    status: str
    requestedAt: str

@dataclass
class PaginationQuery:
    page: int = 1
    size: int = 10

@app.before_serving
async def startup():
    # Initialize cyoda repository/cache and any external connections
    await init_cyoda(cyoda_token)

async def fetch_conversion_rates():
    """
    Fetch Bitcoin-to-USD and Bitcoin-to-EUR conversion rates from an external API.
    Returns dictionary with rates or None if error occurs.
    """
    url = "https://api.coindesk.com/v1/bpi/currentprice/BTC.json"  # Placeholder endpoint
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    # Log error and return None
                    print(f"Error: Received status code {resp.status} from conversion rates API")
                    return None
                data = await resp.json()
    except Exception as ex:
        print(f"Exception fetching conversion rates: {ex}")
        return None

    try:
        rates = {
            "BTC_USD": data["bpi"]["USD"]["rate_float"],
            "BTC_EUR": data["bpi"]["EUR"]["rate_float"]  # Confirm that EUR exists in response.
        }
    except (KeyError, TypeError) as ex:
        print(f"Error parsing conversion rates: {ex}")
        rates = {"BTC_USD": None, "BTC_EUR": None}
    return rates

async def send_email(report):
    """
    Simulate sending an email with the report details.
    Replace this with an actual integration in production.
    """
    try:
        await asyncio.sleep(0.5)  # Simulate network delay
        print(f"Email sent with report: {json.dumps(report)}")
        return "sent"
    except Exception as ex:
        print(f"Error in send_email: {ex}")
        return "failed"

async def process_report(entity):
    """
    Workflow function applied to the entity asynchronously before persistence.
    Performs asynchronous tasks such as fetching conversion rates and sending emails.
    Directly modifies the entity dict; the updated state will be persisted.
    Note: Do not perform entity_service.add/update/delete on the same entity here.
    """
    try:
        # Fetch conversion rates.
        rates = await fetch_conversion_rates()
        if not rates or (rates.get("BTC_USD") is None and rates.get("BTC_EUR") is None):
            entity["status"] = "failed"
            entity["error"] = "Failed to fetch conversion rates"
            return entity

        # Build report details.
        report_details = {
            "report_id": entity.get("job_id", "unknown"),
            "rates": rates,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }
        # Send email with the report details.
        email_status = await send_email(report_details)
        # Update the report details with email status and completion.
        report_details["email_status"] = email_status
        report_details["status"] = "completed"
        # Merge the report details into the original entity.
        entity.update(report_details)
    except Exception as ex:
        # In case of any unexpected exception during processing, mark entity as failed.
        print(f"Exception in process_report workflow: {ex}")
        entity["status"] = "failed"
        entity["error"] = str(ex)
    return entity

@app.route('/job', methods=['POST'])
@validate_request(JobRequest)  # Validation for POST request payload.
@validate_response(JobResponse, 200)
async def create_job(data: JobRequest):
    """
    API endpoint to initiate the report creation process.
    Uses the workflow function 'process_report' to asynchronously enrich the entity
    with conversion rates, email notifications, and updated status before persistence.
    """
    # Generate a unique job id and record timestamp.
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()

    # Initial entity state. Include job_id so that workflow can reference it.
    data_to_store = {
        "job_id": job_id,
        "status": "processing",
        "requestedAt": requested_at
    }

    # Store item in external service using the workflow function.
    # The workflow function 'process_report' will update the entity state asynchronously.
    persisted_job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model=ENTITY_MODEL,
        entity_version=ENTITY_VERSION,  # Always use this constant.
        entity=data_to_store,
        workflow=process_report  # Workflow function applied to the entity prior to persistence.
    )

    return jsonify({
        "report_id": persisted_job_id,
        "status": "Report generation initiated",
        "requestedAt": requested_at
    }), 200

@app.route('/report/<job_id>', methods=['GET'])
async def get_report(job_id: str):
    """
    API endpoint to retrieve a specific report by its ID.
    """
    report = entity_service.get_item(
        token=cyoda_token,
        entity_model=ENTITY_MODEL,
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if report is None:
        return jsonify({"error": "Report not found"}), 404
    return jsonify(report), 200

@validate_querystring(PaginationQuery)  # Validate query parameters for pagination.
@app.route('/reports', methods=['GET'])
async def get_reports():
    """
    API endpoint to retrieve all stored reports with basic pagination.
    """
    try:
        page = int(request.args.get('page', 1))
        size = int(request.args.get('size', 10))
    except ValueError:
        return jsonify({"error": "Invalid pagination parameters"}), 400

    all_reports = entity_service.get_items(
        token=cyoda_token,
        entity_model=ENTITY_MODEL,
        entity_version=ENTITY_VERSION,
    )
    if not all_reports:
        return jsonify({
            "reports": [],
            "total_reports": 0
        }), 200

    # Implement basic pagination logic.
    start = (page - 1) * size
    end = start + size
    reports = all_reports[start:end]
    return jsonify({
        "reports": reports,
        "total_reports": len(all_reports)
    }), 200

if __name__ == '__main__':
    # Run the Quart application.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)