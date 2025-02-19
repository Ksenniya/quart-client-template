from dataclasses import dataclass

from pydantic import HttpUrl
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request
import aiohttp
import pandas as pd
from io import StringIO

app = Quart(__name__)
QuartSchema(app)

# Placeholder for local cache
local_cache = {}

# DTO for request validation using Pydantic

@dataclass
class ReportRequest:
    url: str

@app.route('/report/generate', methods=['POST'])
@validate_request(ReportRequest)
async def generate_report(data: ReportRequest):
    url = data.url

    # Step 1: Download data
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                return jsonify({
                    "status": "error", 
                    "message": "Failed to download data."
                }), 500
            csv_data = await response.text()

    # Step 2: Load data into DataFrame
    try:
        df = pd.read_csv(StringIO(csv_data))
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": f"Failed to load data into DataFrame: {str(e)}"
        }), 500

    # Step 3: Validate DataFrame columns
    expected_columns = [
        "Address", "Neighborhood", "Bedrooms", "Bathrooms", 
        "Square Meters", "Building Age", "Garden", "Garage", 
        "Floors", "Property Type", "Heating Type", "Balcony", 
        "Interior Style", "View", "Materials", "Building Status", 
        "Price (£)"
    ]
    if not all(col in df.columns for col in expected_columns):
        return jsonify({
            "status": "error", 
            "message": "Missing expected columns in data."
        }), 400

    # Step 4: Perform analysis
    average_price = df['Price (£)'].mean()
    property_distribution = df['Property Type'].value_counts().to_dict()
    summary_statistics = {
        "average_bedrooms": df['Bedrooms'].mean(),
        "average_bathrooms": df['Bathrooms'].mean(),
        "average_square_meters": df['Square Meters'].mean()
    }

    # TODO: Generate visualizations and save as URLs
    visualizations = {
        "price_distribution_chart": "URL_to_chart",  # Mock URL
        "property_type_distribution_chart": "URL_to_chart"  # Mock URL
    }

    # Step 5: Create report
    report = {
        "average_price": average_price,
        "property_distribution": property_distribution,
        "summary_statistics": summary_statistics,
        "visualizations": visualizations
    }

    # Store the report in local cache
    local_cache['latest_report'] = report

    return jsonify({"status": "success", "report": report})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000)
