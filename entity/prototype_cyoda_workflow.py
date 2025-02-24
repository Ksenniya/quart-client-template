#!/usr/bin/env python3
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

# Workflow function applied to the "report" entity asynchronously before persistence.
# It takes the initial report data as its only argument, enriches it with external API data,
# simulates email sending and updates the entity state. Any modifications to the entity (report)
# here will be persisted. Note: Do not use entity_service.add/update/delete for the current entity.
async def process_report(report: dict) -> dict:
    # Update the requested timestamp
    report["requestedAt"] = datetime.utcnow().isoformat()

    # Simulate external API call to fetch BTC conversion rates.
    btc_api_url = "https://api.mockcrypto.com/btc_rates"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(btc_api_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    btc_usd = data.get("BTC_USD", 50000)
                    btc_eur = data.get("BTC_EUR", 42000)
                else:
                    btc_usd = 50000  # fallback dummy value
                    btc_eur = 42000  # fallback dummy value
        except Exception as e:
            print(f"Error fetching BTC rates: {e}")
            btc_usd = 50000
            btc_eur = 42000

    # Simulate email sending (fire-and-forget async task could be moved here if needed)
    email_status = "Email sent successfully"

    # Update the report data directly; these changes will be persisted.
    report.update({
        "timestamp": datetime.utcnow().isoformat(),
        "conversion_rates": {
            "BTC_USD": btc_usd,
            "BTC_EUR": btc_eur
        },
        "email_status": email_status,
        "status": "completed"
    })
    return report

# For POST endpoints, we apply validate_request after the route decorator as a workaround for an issue in quart-schema.
@app.route("/job", methods=["POST"])
@validate_request(JobRequest)
async def create_job(data: JobRequest):
    # Generate a unique job id.
    job_id = str(uuid.uuid4())
    initial_data = {
        "report_id": job_id,
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat()
    }
    # Persist the report with the workflow function that processes the entity asynchronously
    # right before saving. All heavy lifting is offloaded from this controller.
    added_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="report",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=initial_data,  # the initial report data
        workflow=process_report  # Workflow function to update the entity state before persistence.
    )
    # Retrieve the persisted report for the response.
    report = await entity_service.get_item(
        token=cyoda_token,
        entity_model="report",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    # Add the external service id to the response.
    report["id"] = added_id if added_id is not None else job_id
    return jsonify(report), 200

@app.route("/report/<string:job_id>", methods=["GET"])
async def get_report(job_id):
    # Retrieve a single report by its ID from the external service.
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
    # Retrieve all stored reports from the external service.
    reports = await entity_service.get_items(
        token=cyoda_token,
        entity_model="report",
        entity_version=ENTITY_VERSION
    )
    return jsonify(reports), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)