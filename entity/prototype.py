import asyncio
import datetime
from quart import Quart, request, jsonify
import aiohttp
from quart_schema import QuartSchema

app = Quart(__name__)
QuartSchema(app)

# Global cache to store brand data
brand_data = []  # TODO: Replace with a persistent storage solution when requirements are clear

# Global dictionary to store job statuses
entity_jobs = {}

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
async def update_brands():
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