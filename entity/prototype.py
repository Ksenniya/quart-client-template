from quart import Quart, request, jsonify
from quart_schema import QuartSchema  # Minimal schema integration
import aiohttp
import asyncio
import uuid
import datetime

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Global in-memory "database" mocks for persistence and jobs
LINKS = {}            # key: link_id, value: link data dict
LINK_BY_HREF = {}     # key: href string, value: link_id (for deduplication)
NEXT_LINK_ID = 1      # Auto-increment link id

JOBS = {}  # key: job_id, value: dict with job status and result summary

# External API endpoints (as provided)
COLLECTION_ENDPOINT = "https://api.weather.gc.ca/collections/hydrometric-stations?f=json&lang=en-CA"
ITEMS_ENDPOINT = ("https://api.weather.gc.ca/collections/hydrometric-stations/items?f=json"
                  "&lang=en-CA&limit=10&additionalProp1=%7B%7D&skipGeometry=false&offset=0")

# Background task to process external data ingestion
async def process_ingestion(job_id):
    global NEXT_LINK_ID
    summary = {
        "ingested": 0,
        "skippedDuplicates": 0,
        "errors": []
    }
    new_links = []  # Temporary list to store all extracted links

    async with aiohttp.ClientSession() as session:
        # Fetch Collection endpoint data
        try:
            async with session.get(COLLECTION_ENDPOINT) as resp:
                if resp.status == 200:
                    collection_data = await resp.json()
                    # Expecting a "links" key with an array of link objects.
                    links_collection = collection_data.get("links", [])
                    new_links.extend(links_collection)
                else:
                    summary["errors"].append(f"Collection endpoint returned {resp.status}")
        except Exception as e:
            summary["errors"].append(f"Exception fetching collection: {str(e)}")

        # Fetch Items endpoint data
        try:
            async with session.get(ITEMS_ENDPOINT) as resp:
                if resp.status == 200:
                    items_data = await resp.json()
                    features = items_data.get("features", [])
                    for feature in features:
                        # Each feature should have a properties object that may contain "links"
                        props = feature.get("properties", {})
                        feature_links = props.get("links", [])
                        new_links.extend(feature_links)
                else:
                    summary["errors"].append(f"Items endpoint returned {resp.status}")
        except Exception as e:
            summary["errors"].append(f"Exception fetching items: {str(e)}")

    # Deduplicate and persist links (mock persistence using in-memory store)
    for link in new_links:
        # Ensure the link has an 'href' key to use for deduplication.
        href = link.get("href")
        if not href:
            # TODO: Handle links without href if needed.
            continue
        if href in LINK_BY_HREF:
            summary["skippedDuplicates"] += 1
        else:
            # Normalize the link entity to include only required attributes
            normalized_link = {
                "id": NEXT_LINK_ID,
                "type": link.get("type"),
                "rel": link.get("rel"),
                "title": link.get("title"),
                "href": href,
                "hreflang": link.get("hreflang")  # Will be None if missing
            }
            LINKS[NEXT_LINK_ID] = normalized_link
            LINK_BY_HREF[href] = NEXT_LINK_ID
            NEXT_LINK_ID += 1
            summary["ingested"] += 1

    # Update job status with result summary and mark finished
    JOBS[job_id]["status"] = "completed"
    JOBS[job_id]["result"] = summary
    JOBS[job_id]["completedAt"] = datetime.datetime.utcnow().isoformat()

# POST endpoint to ingest links (triggers external API calls and processing)
@app.route('/ingest-links', methods=['POST'])
async def ingest_links():
    # Optionally parse incoming JSON if needed (currently dynamic data)
    # TODO: Validate any input parameters if specified in future requirements.
    try:
        data = await request.get_json()  # not used directly, placeholder for future use
    except Exception:
        data = {}
    
    # Create a job entry for asynchronous processing
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()
    JOBS[job_id] = {
        "status": "processing",
        "requestedAt": requested_at,
        "result": None
    }

    # Fire and forget the processing task.
    asyncio.create_task(process_ingestion(job_id))
    
    # Return 202 Accepted with job id information.
    return jsonify({"job_id": job_id, "status": "processing"}), 202

# GET endpoint to retrieve all stored Link Entities
@app.route('/links', methods=['GET'])
async def get_links():
    # Optional query parameters (e.g., pagination) can be added
    # TODO: Implement pagination if needed.
    results = list(LINKS.values())
    return jsonify({"results": results, "total": len(results)}), 200

# GET endpoint to retrieve a specific Link Entity by its id
@app.route('/links/<int:link_id>', methods=['GET'])
async def get_link(link_id: int):
    link = LINKS.get(link_id)
    if not link:
        return jsonify({"error": "Link not found"}), 404
    return jsonify(link), 200

# (Optional) GET endpoint to check the status of an ingestion job.
# This endpoint was not in the original specification, but added as a helper.
@app.route('/jobs/<job_id>', methods=['GET'])
async def get_job(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

# End of prototype.py

# TODO: In a production implementation, replace in-memory persistence with a robust database or cache.
# TODO: Add proper error handling, timeout management, and input validation.
# TODO: Consider implementing retries and logging finer details of external API interactions.
