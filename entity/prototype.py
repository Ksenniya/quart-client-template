import asyncio
import datetime
from dataclasses import dataclass
from quart import Quart, request, jsonify
import aiohttp
from quart_schema import QuartSchema, validate_request  # validate_querystring is not needed as GET /brands has no query parameters

app = Quart(__name__)
QuartSchema(app)

# TODO: Replace with a persistent storage solution when requirements are clear
brand_data = []

entity_jobs = {}

# Dataclass for POST request to update brands
@dataclass
class UpdateTrigger:
    trigger: str  # simple primitive for trigger, e.g., "manual"

# Workaround note:
# For POST endpoints: Route decorator should be first and then the @validate_request decorator.
# For GET endpoints with query parameters, the @validate_querystring decorator should be placed first.
# Since GET /brands has no query parameters, no validation is applied.

async def process_entity(job):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                'https://api.practicesoftwaretesting.com/brands',
                headers={'accept': 'application/json'}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # TODO: Add any necessary data transformation or calculations here
                    global brand_data
                    brand_data = data
                else:
                    # TODO: Improve error handling: retry mechanism or logging as needed
                    print("Error: External API returned status", resp.status)
        except Exception as e:
            # TODO: Implement proper exception handling
            print("Exception occurred during external API call:", e)
    job["status"] = "completed"

@app.route('/brands/update', methods=['POST'])
@validate_request(UpdateTrigger)  # Workaround: For POST endpoints, validation is after the route decorator.
async def update_brands(data: UpdateTrigger):
    job_id = datetime.datetime.utcnow().isoformat()
    entity_job = {
        "status": "processing",
        "requestedAt": job_id
    }
    entity_jobs[job_id] = entity_job
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(entity_job))
    return jsonify({
        "status": "success",
        "message": "Brand data update initiated",
        "job_id": job_id
    })

@app.route('/brands', methods=['GET'])
async def get_brands():
    return jsonify(brand_data)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)