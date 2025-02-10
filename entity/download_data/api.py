# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION

api_bp_download_data = Blueprint('api/download_data', __name__)

@api_bp_download_data.route('/download-data', methods=['GET'])
async def download_data():
    """API endpoint to download London Houses CSV data."""
    try:
        # This endpoint might not use add_item or get_item because it's a download action.
        # Assuming we need to return some data directly instead.
        # This is where you would typically handle the logic to fetch the CSV data.
        
        # For the sake of this example, we're simulating the retrieval of CSV data.
        csv_data = "address,price\n123 London Rd,500000\n456 London St,650000\n"  # Example CSV data
        
        response = jsonify({"data": csv_data})
        response.headers.set("Content-Type", "text/csv")
        response.headers.set("Content-Disposition", "attachment; filename=london_houses.csv")
        
        return response, 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ``` 
# 
# This code snippet implements the `/download-data` endpoint and returns a sample CSV response. Note that since `entity_service` only contains `add_item` and `get_item`, and this endpoint is intended for downloading data, the code handles CSV data directly.