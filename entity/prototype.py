import asyncio
import uuid
import datetime
import json

from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import aiohttp

app = Quart(__name__)
QuartSchema(app)

# In-memory storage (mock persistence)
entity_job = {}


async def fetch_conversion_rates():
    """
    Fetch Bitcoin-to-USD and Bitcoin-to-EUR conversion rates from an external API.
    TODO: Replace the URL and parsing logic as per actual external API requirements.
    """
    # Placeholder API endpoint - using Coindesk as an example.
    url = "https://api.coindesk.com/v1/bpi/currentprice/BTC.json"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                # TODO: Implement proper error handling
                return None
            data = await resp.json()
            # Parse the data as required: extracting USD and EUR values
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
    # Simulate email sending delay
    await asyncio.sleep(0.5)
    print(f"Email sent with report: {json.dumps(report)}")
    return "sent"


async def process_entity(job_id):
    """
    Process the report creation job: fetch rates, store results, and trigger email.
    TODO: Expand exception handling and integrate with proper logging if needed.
    """
    # Record initial timestamp and update status if needed.
    requested_at = entity_job[job_id]["requestedAt"]
    
    rates = await fetch_conversion_rates()
    if not rates:
        # Update the job with an error status
        entity_job[job_id]["status"] = "failed"
        entity_job[job_id]["error"] = "Failed to fetch conversion rates"
        return

    # Create report data with conversion rates and additional metadata.
    report = {
        "report_id": job_id,
        "rates": rates,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }
    
    # Trigger email sending (fire and forget pattern)
    email_status = await send_email(report)  # Alternatively, create a background task if needed.
    report["email_status"] = email_status

    # Update in-memory storage with complete report data.
    entity_job[job_id] = report
    entity_job[job_id]["status"] = "completed"


@app.route('/job', methods=['POST'])
async def create_job():
    """
    API endpoint to initiate the report creation process.
    It fetches BTC conversion rates and triggers an email notification.
    """
    # Create a unique job id
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()
    # Initial job record with status processing
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}
    
    # Fire and forget processing task
    asyncio.create_task(process_entity(job_id))
    
    # Immediately return response with the job id; details will be updated asynchronously.
    return jsonify({
        "report_id": job_id,
        "status": "Report generation initiated",
        "requestedAt": requested_at
    }), 200


@app.route('/report/<job_id>', methods=['GET'])
async def get_report(job_id: str):
    """
    API endpoint to retrieve a specific report by its ID.
    """
    report = entity_job.get(job_id)
    if report is None:
        return jsonify({"error": "Report not found"}), 404
    return jsonify(report), 200


@app.route('/reports', methods=['GET'])
async def get_reports():
    """
    API endpoint to retrieve all stored reports.
    Optional query parameters for pagination can be added as needed.
    """
    # TODO: Implement pagination if the number of reports becomes large.
    reports = list(entity_job.values())
    return jsonify({
        "reports": reports,
        "total_reports": len(reports)
    }), 200


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)