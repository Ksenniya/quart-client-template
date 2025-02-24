#!/usr/bin/env python3
import asyncio
import uuid
from datetime import datetime
from dataclasses import dataclass

import aiohttp
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    # Initialize cyoda service before starting the server.
    await init_cyoda(cyoda_token)

# Dataclass for POST /job validation (no fields required as body is empty)
@dataclass
class JobRequest:
    pass

# Workflow function applied to the "report" entity asynchronously before persistence.
# This function enriches the entity with external API data, simulates sending an email,
# and updates state. Do not call entity_service.add/update/delete for this entity inside this function.
async def process_report(report: dict) -> dict:
    # Update the request timestamp directly.
    report["requestedAt"] = datetime.utcnow().isoformat()
    
    # External API URL for getting BTC conversion rates.
    btc_api_url = "https://api.mockcrypto.com/btc_rates"
    btc_usd = 50000  # Fallback default value.
    btc_eur = 42000  # Fallback default value.
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(btc_api_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    btc_usd = data.get("BTC_USD", btc_usd)
                    btc_eur = data.get("BTC_EUR", btc_eur)
    except Exception as e:
        # Log error and continue with fallback values.
        print(f"Error fetching BTC rates: {e}")
    
    # Simulate email sending (fire-and-forget logic could be placed here if needed).
    email_status = "Email sent successfully"
    
    # Update the report state directly; these changes will be persisted.
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

# POST /job endpoint.
# The endpoint creates an initial report entity and delegates entity state enrichment via the workflow function.
# The controller remains light by moving heavy task responsibilities into process_report().
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
    # Persist the entity using the entity_service.add_item function.
    # The process_report workflow function will asynchronously update the entity state before persistence.
    added_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="report",
        entity_version=ENTITY_VERSION,
        entity=initial_data,
        workflow=process_report
    )
    # Retrieve the persisted report to return in the response.
    report = await entity_service.get_item(
        token=cyoda_token,
        entity_model="report",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    # Use the external service id if available.
    report["id"] = added_id if added_id is not None else job_id
    return jsonify(report), 200

# GET /report/<job_id> endpoint.
# Retrieves a single report entity by its job id.
@app.route("/report/<string:job_id>", methods=["GET"])
async def get_report(job_id):
    report = await entity_service.get_item(
        token=cyoda_token,
        entity_model="report",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if report:
        return jsonify(report), 200
    return jsonify({"error": "Report not found"}), 404

# GET /reports endpoint.
# Retrieves all report entities from the external service.
@app.route("/reports", methods=["GET"])
async def get_reports():
    reports = await entity_service.get_items(
        token=cyoda_token,
        entity_model="report",
        entity_version=ENTITY_VERSION
    )
    return jsonify(reports), 200

if __name__ == '__main__':
    # Run application with debug and threaded enabled.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)