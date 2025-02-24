import asyncio
import uuid
import json
from datetime import datetime
from dataclasses import dataclass

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

app = Quart(__name__)
QuartSchema(app)

# In-memory storage for report data
reports = {}

# Dataclass for POST /job validation (no fields required as body is empty)
@dataclass
class JobRequest:
    pass

# A placeholder for asynchronous processing of the report
async def process_entity(job_id: str) -> dict:
    requested_at = datetime.utcnow().isoformat()
    # Update the report with processing start time
    reports[job_id]["requestedAt"] = requested_at

    # TODO: Replace this URL with the actual external API endpoint for BTC rates.
    btc_api_url = "https://api.mockcrypto.com/btc_rates"

    # Using aiohttp to simulate external API calls.
    async with aiohttp.ClientSession() as session:
        try:
            # NOTE: This is a placeholder API call
            async with session.get(btc_api_url) as resp:
                # For prototype, if the API call fails, use fallback dummy data
                if resp.status == 200:
                    data = await resp.json()
                    # TODO: Adjust extraction logic based on the actual API response structure.
                    btc_usd = data.get("BTC_USD", 50000)
                    btc_eur = data.get("BTC_EUR", 42000)
                else:
                    # Fallback values in case of non-200 responses
                    btc_usd = 50000  # dummy value
                    btc_eur = 42000  # dummy value
        except Exception as e:
            # Log error message and use fallback dummy data
            print(f"Error fetching BTC rates: {e}")
            btc_usd = 50000  # dummy value
            btc_eur = 42000  # dummy value

    # Simulate sending an email report (mock implementation)
    # TODO: Replace with actual email sending logic if needed.
    email_status = "Email sent successfully"

    # Prepare report data
    conversion_rates = {
        "BTC_USD": btc_usd,
        "BTC_EUR": btc_eur
    }
    report = {
        "report_id": job_id,
        "timestamp": datetime.utcnow().isoformat(),
        "conversion_rates": conversion_rates,
        "email_status": email_status,
        "status": "completed"
    }

    # Persist the report in our local cache
    reports[job_id] = report
    return report

# For POST endpoints, we apply validate_request after the route decorator as a workaround for an issue in quart-schema.
@app.route("/job", methods=["POST"])
@validate_request(JobRequest)  # Workaround: For POST endpoints, decorator is applied after route decorator.
async def create_job(data: JobRequest):
    # Generate a unique job id
    job_id = str(uuid.uuid4())
    # Initially store the job as processing
    reports[job_id] = {
        "report_id": job_id,
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat()
    }
    # Fire and forget the processing task (awaited here for prototype simplicity)
    report = await asyncio.create_task(process_entity(job_id))
    # Return report with conversion rates
    return jsonify(report), 200

# GET /report/<job_id> does not require validation decorator as it uses a path parameter.
@app.route("/report/<string:job_id>", methods=["GET"])
async def get_report(job_id):
    # Retrieve a single report by its ID
    report = reports.get(job_id)
    if report:
        return jsonify(report), 200
    return jsonify({"error": "Report not found"}), 404

# GET /reports does not require validation as no request parameters are expected.
@app.route("/reports", methods=["GET"])
async def get_reports():
    # Retrieve all stored reports
    all_reports = list(reports.values())
    return jsonify(all_reports), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)