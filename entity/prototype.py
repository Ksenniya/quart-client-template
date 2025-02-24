import asyncio
import uuid
import datetime
import json

from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring
import aiohttp

app = Quart(__name__)
QuartSchema(app)

# In-memory storage (mock persistence)
entity_job = {}

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
    Process the report creation job: fetch rates, store results, and trigger email.
    TODO: Expand exception handling and integrate with proper logging if needed.
    """
    requested_at = entity_job[job_id]["requestedAt"]
    rates = await fetch_conversion_rates()
    if not rates:
        entity_job[job_id]["status"] = "failed"
        entity_job[job_id]["error"] = "Failed to fetch conversion rates"
        return
    report = {
        "report_id": job_id,
        "rates": rates,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }
    email_status = await send_email(report)  # TODO: Consider fire-and-forget pattern if needed.
    report["email_status"] = email_status
    entity_job[job_id] = report
    entity_job[job_id]["status"] = "completed"

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
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}
    asyncio.create_task(process_entity(job_id))
    return jsonify({
        "report_id": job_id,
        "status": "Report generation initiated",
        "requestedAt": requested_at
    }), 200

# GET endpoint without query parameters - no validation needed.
@app.route('/report/<job_id>', methods=['GET'])
async def get_report(job_id: str):
    """
    API endpoint to retrieve a specific report by its ID.
    """
    report = entity_job.get(job_id)
    if report is None:
        return jsonify({"error": "Report not found"}), 404
    return jsonify(report), 200

# For GET endpoints with query parameters, validation decorators must be placed first.
@validate_querystring(PaginationQuery)  # Workaround: GET validations are placed first.
@app.route('/reports', methods=['GET'])
async def get_reports():
    """
    API endpoint to retrieve all stored reports.
    Optional query parameters for pagination can be added as needed.
    """
    # Access validated query parameters using standard approach.
    page = int(request.args.get('page', 1))
    size = int(request.args.get('size', 10))
    # TODO: Implement pagination logic using page and size.
    reports = list(entity_job.values())
    return jsonify({
        "reports": reports,
        "total_reports": len(reports)
    }), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)