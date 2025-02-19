# ```python
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request
from pydantic import BaseModel, HttpUrl
import aiohttp
import pandas as pd
from io import StringIO
import uuid
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)

class ReportRequest(BaseModel):
    url: HttpUrl

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@app.route('/report/generate', methods=['POST'])
@validate_request
async def generate_report(data: ReportRequest):
    url = data.url
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                return jsonify({"status": "error", "message": "Failed to download data."}), 500
            csv_data = await response.text()
    try:
        df = pd.read_csv(StringIO(csv_data))
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to load data into DataFrame: {str(e)}"}), 500
    expected_columns = ["Address", "Neighborhood", "Bedrooms", "Bathrooms", "Square Meters", "Building Age", "Garden", "Garage", "Floors", "Property Type", "Heating Type", "Balcony", "Interior Style", "View", "Materials", "Building Status", "Price (\u00a3)"]
    if not all(col in df.columns for col in expected_columns):
        return jsonify({"status": "error", "message": "Missing expected columns in data."}), 400
    average_price = df['Price (\u00a3)'].mean()
    property_distribution = df['Property Type'].value_counts().to_dict()
    summary_statistics = {
        "average_bedrooms": df['Bedrooms'].mean(),
        "average_bathrooms": df['Bathrooms'].mean(),
        "average_square_meters": df['Square Meters'].mean()
    }
    visualizations = {
        "price_distribution_chart": "URL_to_chart",
        "property_type_distribution_chart": "URL_to_chart"
    }
    report_id = str(uuid.uuid4())
    report = {
        "id": report_id,
        "average_price": average_price,
        "property_distribution": property_distribution,
        "summary_statistics": summary_statistics,
        "visualizations": visualizations
    }
    entity_service.add_item(token=cyoda_token, entity_model="report", entity_version=ENTITY_VERSION, entity=report)
    return jsonify({"status": "success", "report": report})

@app.route('/report/<report_id>', methods=['GET'])
async def get_report(report_id):
    report = entity_service.get_item(token=cyoda_token, entity_model="report", entity_version=ENTITY_VERSION, technical_id=report_id)
    if report is None:
        return jsonify({"status": "error", "message": "Report not found."}), 404
    return jsonify({"status": "success", "report": report})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
# ```