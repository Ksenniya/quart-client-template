import asyncio
import uuid
import json
from datetime import datetime
from dataclasses import dataclass

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Dataclass for POST /job validation (no fields required as body is empty)
@dataclass
class JobRequest:
    pass

# A placeholder for asynchronous processing of the report
async def process_entity(job_id: str) -> dict:
    requested_at = datetime.utcnow().isoformat()
    # Retrieve the report from the external service
    report = await entity_service.get_item(
        token=cyoda_token,
        entity_model="report",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not report:
        # If report is not found, initialize a new one
        report = {"report_id": job_id}
    report["requestedAt"] = requested_at

    # TODO: Replace this URL with the actual external API endpoint for BTC rates.
    btc_api_url = "https://api.mockcrypto.com/btc_rates"

    # Using aiohttp to simulate external API calls.
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(btc_api_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    btc_usd = data.get("BTC_USD", 50000)
                    btc_eur = data.get("BTC_EUR", 42000)
                else:
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

    conversion_rates = {
        "BTC_USD": btc_usd,
        "BTC_EUR": btc_eur
    }
    report.update({
        "timestamp": datetime.utcnow().isoformat(),
        "conversion_rates": conversion_rates,
        "email_status": email_status,
        "status": "completed"
    })

    # Update the report in the external service
    await entity_service.update_item(
        token=cyoda_token,
        entity_model="report",
        entity_version=ENTITY_VERSION,
        entity=report,
        meta={}
    )
    return report

# For POST endpoints, we apply validate_request after the route decorator as a workaround for an issue in quart-schema.
@app.route("/job", methods=["POST"])
@validate_request(JobRequest)  # Workaround: For POST endpoints, decorator is applied after route decorator.
async def create_job(data: JobRequest):
    # Generate a unique job id
    job_id = str(uuid.uuid4())
    initial_data = {
        "report_id": job_id,
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat()
    }
    # Save the initial report using the external service
    added_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="report",
        entity_version=ENTITY_VERSION,
        entity=initial_data
    )
    # Process the report asynchronously and update it with conversion rates etc.
    report = await asyncio.create_task(process_entity(job_id))
    # Add the external service id to the response for querying by id
    report["id"] = added_id if added_id is not None else job_id
    return jsonify(report), 200

@app.route("/report/<string:job_id>", methods=["GET"])
async def get_report(job_id):
    # Retrieve a single report by its ID from the external service
    report = await entity_service.get_item(
        token=cyoda_token,
        entity_model="report",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if report:
        return jsonify(report), 200
    return jsonify({"error": "Report not found"}), 404

@app.route("/reports", methods=["GET"])
async def get_reports():
    # Retrieve all stored reports from the external service
    reports = await entity_service.get_items(
        token=cyoda_token,
        entity_model="report",
        entity_version=ENTITY_VERSION
    )
    return jsonify(reports), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)