#!/usr/bin/env python3
import asyncio
import datetime
import aiohttp
from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request
from common.config.config import ENTITY_VERSION
from app_init.app_init import cyoda_token, entity_service
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

@app.before_serving
async def startup():
    # Initialize external systems required by the application.
    await init_cyoda(cyoda_token)

# Request schema for fetch endpoint.
@dataclass
class FetchRequest:
    refresh: bool = False  # Indicates if a refresh is forced

# Workflow function for processing an individual brand entity.
# This function is applied to the brand entity before it is persisted.
async def process_brand(entity):
    try:
        # Add a timestamp to indicate when the entity was processed.
        entity["processedAt"] = datetime.datetime.utcnow().isoformat()
        # Here you could add more asynchronous operations such as enriching the brand data.
        # For example, fetch supplementary details from another API.
    except Exception as e:
        # In case of error, log or adjust the entity state accordingly.
        entity["processingError"] = str(e)
    # Return the modified entity. The returned value will be persisted.
    return entity

# Workflow function for processing the brand fetch job entity.
# This function fetches external brand data and adds each brand entity using its specific workflow.
async def process_brands_fetch(job_entity):
    try:
        external_api_url = 'https://api.practicesoftwaretesting.com/brands'
        async with aiohttp.ClientSession() as session:
            async with session.get(external_api_url, headers={"accept": "application/json"}) as resp:
                # Check if response is OK.
                if resp.status == 200:
                    data = await resp.json()
                    processed_count = 0
                    # For each brand item fetched, call add_item with the process_brand workflow.
                    for item in data:
                        try:
                            await entity_service.add_item(
                                token=cyoda_token,
                                entity_model="brands",
                                entity_version=ENTITY_VERSION,
                                entity=item,
                                workflow=process_brand  # Process each brand entity before persistence.
                            )
                            processed_count += 1
                        except Exception as inner_e:
                            # Log the failure for this particular brand entity.
                            # Instead of raising, we attach error information to the item.
                            item["processingError"] = str(inner_e)
                    # Update the job entity state as completed
                    job_entity["status"] = "completed"
                    job_entity["completedAt"] = datetime.datetime.utcnow().isoformat()
                    job_entity["processedCount"] = processed_count
                else:
                    # If the API call did not return 200, store error details.
                    job_entity["status"] = "failed"
                    job_entity["error"] = f"External API error: HTTP {resp.status}"
    except Exception as e:
        # Catch any unexpected errors and update job_entity accordingly.
        job_entity["status"] = "failed"
        job_entity["error"] = str(e)
    # Return the modified job_entity. This is persisted by entity_service.
    return job_entity

# Endpoint to trigger the asynchronous fetching of brand data.
# Instead of handling async tasks in the controller, the workflow function is used.
@app.route('/api/brands/fetch', methods=['POST'])
@validate_request(FetchRequest)
async def fetch_brands(fetch_data: FetchRequest):
    # Generate a unique job identifier using the current UTC timestamp.
    requested_at = datetime.datetime.utcnow().isoformat()
    job_id = f"job_{requested_at}"
    # Initial job entity state.
    job_entity = {
        "jobId": job_id,
        "requestedAt": requested_at,
        "status": "processing"
    }
    # Add the job entity. The workflow function process_brands_fetch will be invoked
    # before persistence, handling the external API call and processing each brand.
    try:
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="brands_fetch_job",
            entity_version=ENTITY_VERSION,
            entity=job_entity,
            workflow=process_brands_fetch
        )
    except Exception as e:
        # If adding the job entity fails, return an error response.
        return jsonify({"status": "failed", "message": str(e)}), 500

    # Return the job id immediately.
    return jsonify({
        "status": "success",
        "message": "Brand data fetch initiated.",
        "jobId": job_id
    })

# Endpoint to retrieve all persisted brand items.
@app.route('/api/brands', methods=['GET'])
async def get_brands():
    try:
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"data": data})

# Endpoint to retrieve a single brand by its identifier.
@app.route('/api/brands/<string:brand_id>', methods=['GET'])
async def get_brand(brand_id: str):
    try:
        brand = await entity_service.get_item(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,
            technical_id=brand_id
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if brand:
        return jsonify(brand)
    return jsonify({"error": "Brand not found"}), 404

if __name__ == '__main__':
    # Run the Quart application with debugging enabled.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)