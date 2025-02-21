Below is the complete updated version of the code. In this version a new workflow function called process_link is defined. This function takes a link entity (a dict), modifies it (for example by adding a timestamp and a "processed" flag), and returns the modified entity. Then, when calling entity_service.add_item, the workflow function is passed as the workflow parameter so that the entity is pre‑processed before being persisted.

------------------------------------------------------------
# prototype.py

from dataclasses import dataclass
from typing import Optional
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response, validate_querystring
import aiohttp
import asyncio
import uuid
import datetime

# Import external service and constants
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# The required startup initialization
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Workflow function that processes the link entity before persistence.
def process_link(link_entity: dict) -> dict:
    # Example logic: add a timestamp and a processed flag to the entity.
    link_entity["processedAt"] = datetime.datetime.utcnow().isoformat()
    link_entity["processed"] = True
    return link_entity

# Data classes for validation
@dataclass
class IngestPayload:
    # Example input for POST /ingest-links. Both fields are optional.
    filter: Optional[str] = None
    force: Optional[bool] = None

@dataclass
class LinkQuery:
    # Example query parameters for GET /links endpoint.
    page: Optional[int] = 1
    pageSize: Optional[int] = 20

# JOBS dictionary for tracking ingestion jobs in memory
JOBS = {}

# External API endpoints (as provided)
COLLECTION_ENDPOINT = "https://api.weather.gc.ca/collections/hydrometric-stations?f=json&lang=en-CA"
ITEMS_ENDPOINT = ("https://api.weather.gc.ca/collections/hydrometric-stations/items?f=json"
                  "&lang=en-CA&limit=10&additionalProp1=%7B%7D&skipGeometry=false&offset=0")

# Background task to process external data ingestion
async def process_ingestion(job_id):
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

    # Iterate new links and deduplicate based on the "href" field.
    for link in new_links:
        href = link.get("href")
        if not href:
            # Skip links without href.
            continue

        # Check for duplicate using the external entity_service.
        # We assume that get_items_by_condition returns a list of items.
        try:
            existing_links = await entity_service.get_items_by_condition(
                token=cyoda_token,
                entity_model="link",
                entity_version=ENTITY_VERSION,
                condition={"href": href}
            )
        except Exception as e:
            summary["errors"].append(f"Error checking duplicate for href {href}: {str(e)}")
            continue

        if existing_links and len(existing_links) > 0:
            summary["skippedDuplicates"] += 1
        else:
            # Normalize the link entity to include only required attributes.
            normalized_link = {
                "type": link.get("type"),
                "rel": link.get("rel"),
                "title": link.get("title"),
                "href": href,
                "hreflang": link.get("hreflang")  # Will be None if missing
            }
            try:
                # Persist the link using the external service with the workflow function.
                new_id = await entity_service.add_item(
                    token=cyoda_token,
                    entity_model="link",
                    entity_version=ENTITY_VERSION,  # always use this constant
                    entity=normalized_link,           # the validated data object
                    workflow=process_link             # workflow function applied before persistence
                )
                # Add the generated id to the normalized link for reference.
                normalized_link["id"] = new_id
                summary["ingested"] += 1
            except Exception as e:
                summary["errors"].append(f"Error inserting link with href {href}: {str(e)}")

    # Update job status with result summary and mark finished.
    JOBS[job_id]["status"] = "completed"
    JOBS[job_id]["result"] = summary
    JOBS[job_id]["completedAt"] = datetime.datetime.utcnow().isoformat()

# POST endpoint to ingest links (triggers external API calls and processing)
# NOTE: For POST endpoints, we place the route decorator first, then validation decorators,
# which is a known workaround for the quart-schema library issue.
@app.route('/ingest-links', methods=['POST'])
@validate_request(IngestPayload)    # Validate the request body (if provided)
@validate_response(dict, 202)       # Validate the response; here we use dict as generic type.
async def ingest_links(data: IngestPayload):
    # The validated data is available as "data", though it's not currently used.
    # TODO: Use validated payload fields if necessary.

    # Create a job entry for asynchronous processing.
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

# GET endpoint to retrieve all stored Link Entities with query parameters validation.
# For GET endpoints, the validation decorator is placed before the route decorator
# and we do not pass the validated object as function argument.
@validate_querystring(LinkQuery)  # Workaround: validation decorator must be first for GET requests.
@app.route('/links', methods=['GET'])
async def get_links():
    # Retrieve query parameters using request.args (the validated values are not automatically injected).
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('pageSize', 20, type=int)
    # Retrieve all link entities from the external entity_service.
    try:
        # The external service is in charge of pagination in a production scenario.
        links = await entity_service.get_items(
            token=cyoda_token,
            entity_model="link",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        return jsonify({"error": f"Unable to retrieve links: {str(e)}"}), 500

    # Return the list. (If needed, you can perform pagination on the returned result)
    return jsonify({"results": links, "total": len(links) if isinstance(links, list) else 0}), 200

# GET endpoint to retrieve a specific Link Entity by its id (no validation needed)
@app.route('/links/<int:link_id>', methods=['GET'])
async def get_link(link_id: int):
    try:
        link = await entity_service.get_item(
            token=cyoda_token,
            entity_model="link",
            entity_version=ENTITY_VERSION,
            technical_id=link_id
        )
    except Exception as e:
        return jsonify({"error": f"Error retrieving link: {str(e)}"}), 500

    if not link:
        return jsonify({"error": "Link not found"}), 404
    return jsonify(link), 200

# (Optional) GET endpoint to check the status of an ingestion job (no validation needed)
@app.route('/jobs/<job_id>', methods=['GET'])
async def get_job(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

# End of prototype.py
------------------------------------------------------------

In this version, any time a new link entity is added (for example from the ingestion process), the process_link workflow function is executed on the normalized link entity before persistence by the entity_service. This ensures your entity can be further processed (modified, enriched, etc.) in a centralized manner before it is stored.