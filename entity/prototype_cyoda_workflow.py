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
    await init_cyoda(cyoda_token)

async def fetch_conversion_rates():
    """
    Fetch Bitcoin-to-USD and Bitcoin-to-EUR conversion rates from an external API.
    TODO: Replace the URL and parsing logic as per actual external API requirements.
    """
    url = "https://api.coindesk.com/v1/bpi/currentprice/BTC.json"  # Placeholder endpoint
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                # TODO: Implement proper error handling
                return None
            data = await resp.json()
            try:
                rates = {
                    "BTC_USD": data["bpi"]["USD"]["rate_float"],
                    "BTC_EUR": data["bpi"]["EUR"]["rate_float"]  # TODO: Confirm that EUR exists in response; Coindesk API may not provide EUR.
                }
            except KeyError:
                # TODO: Consider returning an error or default values.
                rates = {"BTC_USD": None, "BTC_EUR": None}
            return rates

async def send_email(report):
    """
    Simulate sending an email with the report details.
    TODO: Replace this with an actual email service integration.
    """
    await asyncio.sleep(0.5)  # Simulate delay
    print(f"Email sent with report: {json.dumps(report)}")
    return "sent"

async def process_entity(job_id):
    """
    Process the report creation job: fetch rates, update report and trigger email.
    """
    # Retrieve existing item details from external service
    report_record = entity_service.get_item(
        token=cyoda_token,
        entity_model="{entity_name}",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    requested_at = report_record.get("requestedAt")

    rates = await fetch_conversion_rates()
    if not rates:
        # Update record with failure state
        report_record["status"] = "failed"
        report_record["error"] = "Failed to fetch conversion rates"
        entity_service.update_item(
            token=cyoda_token,
            entity_model="{entity_name}",
            entity_version=ENTITY_VERSION,
            entity=report_record,
            meta={}
        )
        return

    report = {
        "report_id": job_id,
        "rates": rates,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }
    email_status = await send_email(report)
    # Update report with email status and mark as completed
    report["email_status"] = email_status
    report["status"] = "completed"
    # Update record with final report details
    entity_service.update_item(
        token=cyoda_token,
        entity_model="{entity_name}",
        entity_version=ENTITY_VERSION,
        entity=report,
        meta={}
    )

def process_report(entity):
    # Workflow function applied to the entity data before persistence.
    # Here we can modify the entity's state.
    entity["workflow_processed"] = True
    entity["processed_at"] = datetime.datetime.utcnow().isoformat()
    return entity

# For POST endpoints, validation decorators are placed after the route decorator.
@app.route('/job', methods=['POST'])
@validate_request(JobRequest)  # Workaround: Decorator order - POST validations placed after route.
@validate_response(JobResponse, 200)
async def create_job(data: JobRequest):
    """
    API endpoint to initiate the report creation process.
    It fetches BTC conversion rates and triggers an email notification.
    """
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()
    data_to_store = {
        "status": "processing",
        "requestedAt": requested_at
    }
    # Store item in external service and obtain its id.
    # The workflow function 'process_report' is applied asynchronously before persistence.
    job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="{entity_name}",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=data_to_store,  # the validated data object
        workflow=process_report  # Workflow function applied to the entity before persistence.
    )
    # Process the job asynchronously.
    asyncio.create_task(process_entity(job_id))
    return jsonify({
        "report_id": job_id,
        "status": "Report generation initiated",
        "requestedAt": requested_at
    }), 200

# GET endpoint to retrieve a specific report by its ID.
@app.route('/report/<job_id>', methods=['GET'])
async def get_report(job_id: str):
    """
    API endpoint to retrieve a specific report by its ID.
    """
    report = entity_service.get_item(
        token=cyoda_token,
        entity_model="{entity_name}",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if report is None:
        return jsonify({"error": "Report not found"}), 404
    return jsonify(report), 200

# GET endpoint to retrieve all stored reports with optional pagination.
@validate_querystring(PaginationQuery)  # Workaround: GET validations are placed first.
@app.route('/reports', methods=['GET'])
async def get_reports():
    """
    API endpoint to retrieve all stored reports.
    Optional query parameters for pagination can be added as needed.
    """
    page = int(request.args.get('page', 1))
    size = int(request.args.get('size', 10))
    all_reports = entity_service.get_items(
        token=cyoda_token,
        entity_model="{entity_name}",
        entity_version=ENTITY_VERSION,
    )
    # Implement basic pagination logic
    start = (page - 1) * size
    end = start + size
    reports = all_reports[start:end] if all_reports else []
    return jsonify({
        "reports": reports,
        "total_reports": len(all_reports) if all_reports else 0
    }), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)