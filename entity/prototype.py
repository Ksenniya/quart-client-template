Below is a working prototype for prototype.py. Note that this implementation uses a global in-memory cache for persistence and mock calls for the LEI data source. Wherever a placeholder is used, a TODO comment is added.

───────────────────────────── Begin Code ─────────────────────────────

#!/usr/bin/env python3
import asyncio
import uuid
import datetime
import json
from quart import Quart, request, jsonify
from quart_schema import QuartSchema  # just one-line integration as specified
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # Integrate QuartSchema

# Global in-memory cache for jobs and results
entity_jobs = {}

# Base URL for the Finnish Companies Registry API (PRH Avoindata API)
PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3"

# Placeholder URL for LEI data source
LEI_API_URL = "https://mock-lei-service.example.com/getLei"  # TODO: Replace with official endpoint

async def fetch_companies_from_prh(company_name, filters):
    """
    Query PRH API for companies
    """
    params = {"name": company_name}
    # TODO: Map filters to the proper query parameters if needed.
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{PRH_API_BASE}/companies", params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("results", [])  # TODO: Adjust based on actual API response structure.
            else:
                # Log error or handle error appropriately
                return []  # Return empty list on error

async def fetch_lei_for_company(company):
    """
    Mock function to retrieve LEI for a company.
    In a real implementation, this should call an official LEI registry.
    """
    # TODO: Replace this mock with actual logic to query the LEI service.
    # For now we simulate a network call with asyncio.sleep
    await asyncio.sleep(0.2)  # Simulate network delay
    # Let's assume that for this prototype, companies with an even length name get a valid LEI.
    if len(company.get("companyName", "")) % 2 == 0:
        return "VALID_LEI_MOCK"
    else:
        return "Not Available"

def is_company_active(company):
    """
    Determine whether a company is active.
    Assumes that company has a field "status" with value "Active" if active.
    TODO: Adjust logic if the actual data structure is different.
    """
    return company.get("status", "").lower() == "active"

async def process_entity(job_id, payload):
    """
    The background task that processes the company search and enrichment.
    """
    try:
        company_name = payload.get("companyName")
        filters = payload.get("filters", {})

        # 1. Retrieve companies from PRH API
        companies = await fetch_companies_from_prh(company_name, filters)

        # 2. Filter only active companies
        active_companies = [company for company in companies if is_company_active(company)]

        # 3. For each active company, fetch LEI information
        enriched_companies = []
        for company in active_companies:
            lei = await fetch_lei_for_company(company)
            # Build enriched company record
            enriched_company = {
                "companyName": company.get("companyName", "Unknown"),  # TODO: adjust key names per PRH API response
                "businessId": company.get("businessId", "Unknown"),       # TODO: adjust accordingly
                "companyType": company.get("companyType", "Unknown"),     # TODO: adjust accordingly
                "registrationDate": company.get("registrationDate", "Unknown"),  # TODO: adjust accordingly
                "status": "Active",
                "LEI": lei
            }
            enriched_companies.append(enriched_company)

        # 4. Save the final job result (in local cache)
        entity_jobs[job_id]["results"] = enriched_companies
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["completedAt"] = datetime.datetime.utcnow().isoformat()

    except Exception as e:
        # If any exception occurs, mark as error with a message.
        entity_jobs[job_id]["status"] = "error"
        entity_jobs[job_id]["error"] = str(e)
        # TODO: Add proper logging here.

@app.route("/companies/search", methods=["POST"])
async def search_companies():
    """
    POST endpoint to trigger company search and enrichment.
    """
    payload = await request.get_json()
    if not payload or "companyName" not in payload:
        return jsonify({"error": "companyName is required"}), 400

    search_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()

    # Save job to local in-memory cache
    entity_jobs[search_id] = {
        "status": "processing",
        "requestedAt": requested_at,
        "results": None
    }
    
    # Fire and forget the background processing task
    # Using asyncio.create_task to process the job asynchronously
    asyncio.create_task(process_entity(search_id, payload))

    return jsonify({
        "searchId": search_id,
        "status": "processing",
        "message": "Your search is being processed."
    })

@app.route("/companies/results/<job_id>", methods=["GET"])
async def get_search_results(job_id):
    """
    GET endpoint to retrieve the stored search and enrichment results.
    """
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Invalid searchId"}), 404

    if job["status"] == "processing":
        return jsonify({
            "searchId": job_id,
            "status": "processing",
            "message": "Your search is still being processed, please try again later."
        })

    if job["status"] == "error":
        return jsonify({
            "searchId": job_id,
            "status": "error",
            "message": "There was an error processing your search.",
            "error": job.get("error")
        })

    # Assume status completed
    return jsonify({
        "searchId": job_id,
        "results": job.get("results", []),
        "metadata": {
            "requestedAt": job.get("requestedAt"),
            "completedAt": job.get("completedAt"),
            "resultCount": len(job.get("results", []))
        }
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

───────────────────────────── End Code ─────────────────────────────

This prototype code uses aiohttp to asynchronously call the PRH API and a mock LEI service. It processes the job in the background and uses in-memory storage for persistence. Feel free to adjust the TODO comments as further details become available.