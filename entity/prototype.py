from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response
import aiohttp
import pandas as pd
import io

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# In-memory cache to simulate persistence
reports_cache = {}

# Data Models

@dataclass
class DataDownloadRequest:
    url: str

@dataclass
class DataDownloadResponse:
    message: str
    report_id: str

@dataclass
class AnalysisFilters:
    property_type: str = None
    neighborhood: str = None

@dataclass
class DataAnalysisRequest:
    filters: AnalysisFilters

@dataclass
class DataAnalysisResponse:
    message: str
    report_url: str
    average_price: float
    property_type_distribution: dict

# Endpoints

@app.route('/reports', methods=['POST'])
@validate_request(DataDownloadRequest)
@validate_response(DataDownloadResponse, 201)
async def download_data(data: DataDownloadRequest):
    url = data.url
    
    if not url:
        return jsonify({"error": "URL is required."}), 400
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return jsonify({"error": "Failed to download data."}), 500
                
                content = await response.text()
                # TODO: Validate and process the CSV content thoroughly
                # Using io.StringIO to create a file-like object from string
                df = pd.read_csv(io.StringIO(content))
                
                # Cache the DataFrame to simulate persistence
                report_id = str(len(reports_cache) + 1)
                reports_cache[report_id] = df
                return DataDownloadResponse(message="Data downloaded successfully.", report_id=report_id), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/reports/<report_id>/download', methods=['GET'])
async def download_report(report_id):
    # TODO: Generate a detailed report in PDF/HTML format
    if report_id not in reports_cache:
        return jsonify({"error": "Report not found."}), 404
    
    # Placeholder report content (plain text for now)
    report_content = f"Report for ID {report_id}:\n"
    report_content += str(reports_cache[report_id].describe())
    
    return report_content, 200, {'Content-Type': 'text/plain'}

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)