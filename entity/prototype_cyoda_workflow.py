Below is one complete, refactored version of the application. In this version we have moved as much business logic as possible out of the HTTP controllers and into dedicated “workflow” and helper functions. In particular, the asynchronous ingestion work is now split into several dedicated functions:

• fetch_external_links – contacts external endpoints (collection and items) and returns a consolidated list of links.  
• process_link – a workflow function that is invoked by the persistence layer (via entity_service.add_item) to perform pre‑persistence modifications on a link entity (for example, adding a timestamp and setting a processed flag).  
• deduplicate_and_persist_link – checks whether the link already exists by its “href” attribute and, if not, calls entity_service.add_item with process_link as its workflow parameter.  
• process_ingestion – the fire‑and‑forget function (previously all inside the endpoint) that calls fetch_external_links and iterates over each link, invoking deduplicate_and_persist_link for every candidate. It also updates the job summary accordingly.  

By isolating this logic into separate functions we “free” the controllers from excessive logic while making the overall flow easier to test and maintain. We have also inserted additional error handling (guarding against unexpected exceptions) and notes about potential pitfalls (for example, avoiding infinite recursion if a workflow on the same entity type internally calls entity_service.add_item).

Below is the full code:

------------------------------------------------------------
#!/usr/bin/env python3
# prototype.py

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
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

# ---------------------- Startup Initialization ---------------------- #
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# ---------------------- Workflow and Helper Functions ---------------------- #

def process_link(link_entity: dict) -> dict:
    """
    Workflow function for a Link entity. This function is invoked inside entity_service.add_item
    via the workflow parameter. It may add, modify, or remove data on the entity.
    """
    try:
        # For example: add the current UTC timestamp and a processed flag.
        link_entity["processedAt"] = datetime.datetime.utcnow().isoformat()
        link_entity["processed"] = True
    except Exception as e:
        # In production, log the error
        link_entity["workflowError"] = str(e)
    return link_entity

async def fetch_collection_links(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    """
    Fetches links from the COLLECTION_ENDPOINT.
    Returns a list of link dictionaries.
    """
    collection_endpoint = "https://api.weather.gc.ca/collections/hydrometric-stations?f=json&lang=en-CA"
    links = []
    try:
        async with session.get(collection_endpoint) as resp:
            if resp.status == 200:
                data = await resp.json()
                links = data.get("links", [])
            else:
                # In a real scenario, log this error
                raise Exception(f"Collection endpoint returned {resp.status}")
    except Exception as e:
        raise Exception(f"Exception fetching collection: {str(e)}")
    return links

async def fetch_items_links(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    """
    Fetches links found within the features of the ITEMS_ENDPOINT.
    Returns a list of link dictionaries.
    """
    items_endpoint = ("https://api.weather.gc.ca/collections/hydrometric-stations/items?f=json"
                      "&lang=en-CA&limit=10&additionalProp1=%7B%7D&skipGeometry=false&offset=0")
    links = []
    try:
        async with session.get(items_endpoint) as resp:
            if resp.status == 200:
                data = await resp.json()
                features = data.get("features", [])
                for feature in features:
                    props = feature.get("properties", {})
                    feature_links = props.get("links", [])
                    links.extend(feature_links)
            else:
                raise Exception(f"Items endpoint returned {resp.status}")
    except Exception as e:
        raise Exception(f"Exception fetching items: {str(e)}")
    return links

async def fetch_external_links() -> List[Dict[str, Any]]:
    """
    Contacts external endpoints and returns a consolidated list of link dictionaries.
    Any issues are caught and surfaced to the caller via exceptions.
    """
    links: List[Dict[str, Any]] = []
    async with aiohttp.ClientSession() as session:
        # Gather links from both endpoints separately.
        try:
            collection_links = await fetch_collection_links(session)
            links.extend(collection_links)
        except Exception as e:
            # In production, log or report the error
            links.append({"error": f"Collection error: {str(e)}"})
        
        try:
            items_links = await fetch_items_links(session)
            links.extend(items_links)
        except Exception as e:
            links.append({"error": f"Items error: {str(e)}"})
    return links

async def deduplicate_and_persist_link(link: Dict[str, Any], summary: Dict[str, Any]) -> None:
    """
    Checks if the link already exists using entity_service.get_items_by_condition.
    If not a duplicate, normalizes the link and calls entity_service.add_item with the 
    process_link workflow function. Updates the provided summary dict accordingly.
    """
    href = link.get("href")
    if not href:
        # Skip links without an href.
        return

    try:
        existing_links = await entity_service.get_items_by_condition(
            token=cyoda_token,
            entity_model="link",
            entity_version=ENTITY_VERSION,
            condition={"href": href}
        )
    except Exception as e:
        summary["errors"].append(f"Error checking duplicate for href {href}: {str(e)}")
        return

    if existing_links and len(existing_links) > 0:
        summary["skippedDuplicates"] += 1
    else:
        # Normalize the link entity (only include required attributes).
        normalized_link = {
            "type": link.get("type"),
            "rel": link.get("rel"),
            "title": link.get("title"),
            "href": href,
            "hreflang": link.get("hreflang")  # May be None if missing.
        }
        try:
            # IMPORTANT: We pass process_link as the workflow function.
            # Note: Ensure that process_link itself does not call any persistence methods on "link"
            # to avoid infinite recursion.
            new_id = await entity_service.add_item(
                token=cyoda_token,
                entity_model="link",
                entity_version=ENTITY_VERSION,  # Always use this constant.
                entity=normalized_link,
                workflow=process_link
            )
            # Add the generated id to the normalized link (for reference)
            normalized_link["id"] = new_id
            summary["ingested"] += 1
        except Exception as e:
            summary["errors"].append(f"Error inserting link with href {href}: {str(e)}")

async def process_ingestion(job_id: str) -> None:
    """
    The fire-and-forget asynchronous task that performs external data ingestion.
    It fetches external links, iterates over each, performs duplicate checking and persists
    new entries using deduplicate_and_persist_link. It then updates the JOBS entry with a summary.
    """
    summary = {
        "ingested": 0,
        "skippedDuplicates": 0,
        "errors": []
    }
    try:
        external_links = await fetch_external_links()
    except Exception as e:
        summary["errors"].append(f"Failed to fetch external links: {str(e)}")
        external_links = []
    
    # Process each link and catch any potential issues.
    for link in external_links:
        # If a link contains an "error" key as added by fetch_external_links, skip it.
        if "error" in link:
            summary["errors"].append(link["error"])
            continue
        await deduplicate_and_persist_link(link, summary)
    
    # Update job status with result summary and mark as completed.
    JOBS[job_id]["status"] = "completed"
    JOBS[job_id]["result"] = summary
    JOBS[job_id]["completedAt"] = datetime.datetime.utcnow().isoformat()

# ---------------------- Data Classes for Request/Response ---------------------- #
@dataclass
class IngestPayload:
    # Example input for POST /ingest-links.
    filter: Optional[str] = None
    force: Optional[bool] = None

@dataclass
class LinkQuery:
    # Example query parameters for GET /links endpoint.
    page: Optional[int] = 1
    pageSize: Optional[int] = 20

# In-memory JOBS dictionary (used only to track ingestion job status)
JOBS: Dict[str, Dict[str, Any]] = {}

# ---------------------- REST API Endpoints (Controllers) ---------------------- #

@app.route('/ingest-links', methods=['POST'])
@validate_request(IngestPayload)    # Validate incoming request body.
@validate_response(dict, 202)       # Validate outgoing response type.
async def ingest_links(data: IngestPayload):
    """
    POST endpoint to ingest links.
    This endpoint only creates a JOB entry and fires off the asynchronous process_ingestion
    task. All ingestion logic is handled via workflow helper functions.
    """
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()
    JOBS[job_id] = {
        "status": "processing",
        "requestedAt": requested_at,
        "result": None
    }
    try:
        # Fire-and-forget: process_ingestion is detached so that the controller immediately responds.
        asyncio.create_task(process_ingestion(job_id))
    except Exception as e:
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["result"] = {"errors": [f"Failed to start background task: {str(e)}"]}
        return jsonify({"job_id": job_id, "status": "failed"}), 500

    return jsonify({"job_id": job_id, "status": "processing"}), 202

@validate_querystring(LinkQuery)  # For GET requests we first validate query parameters.
@app.route('/links', methods=['GET'])
async def get_links():
    """
    GET endpoint to retrieve all stored Link entities.
    This controller delegates to the external service. In production, proper pagination should be handled.
    """
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('pageSize', 20, type=int)

    try:
        links = await entity_service.get_items(
            token=cyoda_token,
            entity_model="link",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        return jsonify({"error": f"Unable to retrieve links: {str(e)}"}), 500

    total = len(links) if isinstance(links, list) else 0
    # Optionally, perform in-memory pagination if entity_service does not handle it.
    start = (page - 1) * page_size
    end = start + page_size
    paginated_results = links[start:end] if isinstance(links, list) else links

    return jsonify({"results": paginated_results, "total": total}), 200

@app.route('/links/<int:link_id>', methods=['GET'])
async def get_link(link_id: int):
    """
    GET endpoint to retrieve a single Link entity based on its technical id.
    """
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

@app.route('/jobs/<job_id>', methods=['GET'])
async def get_job(job_id: str):
    """
    GET endpoint to check the status of an asynchronous ingestion job.
    """
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(job), 200

# ---------------------- Main Application ---------------------- #
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

# End of prototype.py
------------------------------------------------------------

Notes and Reasoning:
1. The external fetching logic is grouped into small helper functions so that network errors can be caught, logged, and even inserted into the summary as errors.  
2. Process_ingestion no longer mixes HTTP concerns with business logic. Instead, it calls fetch_external_links and then iterates through each potential link, delegating duplicate checking and persistence to deduplicate_and_persist_link.  
3. The process_link workflow function ensures that any transformation needed before persisting a Link is done in one place. This “freeing” of the controllers makes them lean and focused on request/response handling only.  
4. We guard against missing or faulty data (for example, links without a valid href) and also avoid a scenario where process_link might trigger infinite recursion (by not calling persistence methods on a “link” which is being processed).  
5. The JOBS dictionary and associated endpoints provide a simple way to monitor asynchronous background tasks.

This refactored application divides concerns in a robust and flexible manner and helps prevent common issues that might arise when business logic clutters controller implementations.