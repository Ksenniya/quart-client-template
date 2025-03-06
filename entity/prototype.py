import asyncio
import datetime
import io
import logging
import uuid

import httpx
import pandas as pd
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory persistence for reports
reports_cache = {}

@app.route("/data/analyze", methods=["POST"])
async def analyze_data():
    try:
        req = await request.get_json()
        data_source_url = req.get("data_source_url")
        analysis_params = req.get("analysis_params", {})

        if not data_source_url:
            return jsonify({"error": "data_source_url is required"}), 400

        # Generate a unique report id and record the initial status.
        report_id = str(uuid.uuid4())
        requested_at = datetime.datetime.utcnow().isoformat() + "Z"
        reports_cache[report_id] = {"status": "processing", "requestedAt": requested_at}

        # Fire and forget the processing task.
        asyncio.create_task(process_data(report_id, data_source_url, analysis_params))

        return jsonify({
            "status": "analysis_started",
            "report_id": report_id,
            "message": "Data analysis has been started. Please check back later for the result."
        }), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500

async def process_data(report_id, data_source_url, analysis_params):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(data_source_url)
        response.raise_for_status()

        csv_content = response.text
        # Read CSV data using pandas.
        df = pd.read_csv(io.StringIO(csv_content))
        
        # TODO: Apply additional data filtering and transformation based on analysis_params.
        filters = analysis_params.get("filters", {})
        if "min_price" in filters and "price" in df.columns:
            df = df[df["price"] >= filters["min_price"]]
        if "max_price" in filters and "price" in df.columns:
            df = df[df["price"] <= filters["max_price"]]

        # Calculate summary statistics for provided metrics.
        metrics = analysis_params.get("metrics", [])
        analysis_result = {}
        for metric in metrics:
            if metric in df.columns:
                analysis_result[metric] = df[metric].describe().to_dict()
            else:
                analysis_result[metric] = f"Metric '{metric}' not found in data."
        
        # Create a simple report. In a complete solution, this might be written to a file (e.g., CSV or PDF).
        report = {
            "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
            "analysis": analysis_result
        }

        # Update the cache with the completed report.
        reports_cache[report_id] = {"status": "available", "report": report, "generated_at": datetime.datetime.utcnow().isoformat() + "Z"}
        logger.info(f"Report {report_id} generated successfully.")
    
    except Exception as e:
        logger.exception(e)
        reports_cache[report_id] = {"status": "failed", "error": str(e)}

@app.route("/reports/<report_id>", methods=["GET"])
async def get_report(report_id):
    report_entry = reports_cache.get(report_id)
    if not report_entry:
        return jsonify({"error": "Report not found."}), 404
    
    return jsonify({
        "report_id": report_id,
        "status": report_entry.get("status"),
        "report": report_entry.get("report", None),
        "error": report_entry.get("error", None)
    })

@app.route("/reports", methods=["GET"])
async def list_reports():
    # List all reports with basic metadata.
    report_list = []
    for report_id, data in reports_cache.items():
        report_list.append({
            "report_id": report_id,
            "status": data.get("status"),
            "generated_at": data.get("generated_at", None),
            "requested_at": data.get("requestedAt", None)
        })
    return jsonify({"reports": report_list})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)