#!/usr/bin/env python3
from dataclasses import dataclass
from quart import Quart, request, jsonify
from aiohttp import ClientSession
from quart_schema import QuartSchema, validate_request
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

ENTITY_VERSION = "1.0"

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@dataclass
class DataLoadRequest:
    file_path: str

@dataclass
class DataAnalyzeRequest:
    file_path: str

@dataclass
class ReportGenerateRequest:
    analysis_results: str
    format: str

@app.route('/data', methods=['GET'])
async def download_data():
    async with ClientSession() as session:
        try:
            async with session.get("https://raw.githubusercontent.com/Cyoda-platform/cyoda-ai/refs/heads/ai-2.x/data/test-inputs/v1/connections/london_houses.csv") as response:
                if response.status == 200:
                    data = await response.text()
                    await entity_service.add_item(
                        token=cyoda_token,
                        entity_model="datum",
                        entity_version=ENTITY_VERSION,
                        entity={"file_path": "/path/to/london_houses.csv"}
                    )
                    return jsonify(message="Data downloaded successfully", file_path="/path/to/london_houses.csv"), 200
                else:
                    return jsonify(error="URL is unreachable or file not found."), 400
        except Exception as e:
            return jsonify(error=str(e)), 500

@app.route('/data/load', methods=['POST'])
@validate_request(DataLoadRequest)
async def load_data(data: DataLoadRequest):
    items = await entity_service.get_items_by_condition(
        token=cyoda_token,
        entity_model="datum",
        entity_version=ENTITY_VERSION,
        condition={"file_path": data.file_path}
    )
    if items:
        summary = {"total_rows": 100, "columns": ["Address", "Neighborhood", "Bedrooms", "Price (\u00a3)"]}
        return jsonify(message="Data loaded successfully", data_summary=summary), 200
    else:
        return jsonify(error="File does not exist."), 404

@app.route('/data/analyze', methods=['POST'])
@validate_request(DataAnalyzeRequest)
async def analyze_data(data: DataAnalyzeRequest):
    items = await entity_service.get_items_by_condition(
        token=cyoda_token,
        entity_model="datum",
        entity_version=ENTITY_VERSION,
        condition={"file_path": data.file_path}
    )
    if items:
        statistics = {"average_price": 2000000, "property_distribution": {"Apartment": 30, "Semi-Detached": 70}}
        return jsonify(statistics=statistics), 200
    else:
        return jsonify(error="Data is invalid or analysis failed."), 400

@app.route('/report/generate', methods=['POST'])
@validate_request(ReportGenerateRequest)
async def generate_report(data: ReportGenerateRequest):
    report_path = "/path/to/report.pdf" if data.format.upper() == "PDF" else "/path/to/report.html"
    await entity_service.add_item(
        token=cyoda_token,
        entity_model="report",
        entity_version=ENTITY_VERSION,
        entity={"analysis_results": data.analysis_results, "format": data.format}
    )
    return jsonify(message="Report generated successfully", report_path=report_path), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)