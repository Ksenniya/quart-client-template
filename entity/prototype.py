Below is an example prototype.py that implements a working prototype based on your requirements. This prototype uses Quart as the web framework, aiohttp.ClientSession for external HTTP requests, an in‐memory dictionary for temporary persistence, and QuartSchema(app) for schema integration. Mocks and placeholders are annotated with TODO comments where additional enhancement is needed.

--------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
import json
from quart import Quart, request, jsonify, Response
from quart_schema import QuartSchema  # Only added one line as requested
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # Integrate QuartSchema

# Global in-memory "cache" for job results
entity_jobs = {}  # Dictionary: key=job_id, value=dict with status and results

# Constants for external service URLs
PRH_API_BASE_URL = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
# TODO: Replace with actual LEI service endpoint when available.
LEI_API_URL = "https://example.com/lei"  # Placeholder URL

@app.route("/companies/search", methods=["POST"])
async def search_companies():
    try:
        data = await request.get_json()
        # Validate required field "company_name"
        if not data or "company_name" not in data:
            return jsonify({"error": "company_name is required"}), 400

        company_name = data.get("company_name")
        # Additional filters can be gathered from data if required.
        job_id = str(uuid.uuid4())
        requested_at = datetime.datetime.utcnow().isoformat()
        # Save initial job state
        entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at, "results": None}

        # Fire and forget processing task.
        asyncio.create_task(process_entity(job_id, data))
        return jsonify({"search_id": job_id, "status": "processing"})
    except Exception as e:
        # TODO: Enhance error handling as needed.
        return jsonify({"error": str(e)}), 500

@app.route("/companies/search/<job_id>", methods=["GET"])
async def get_search_results(job_id: str):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job ID not found"}), 404
    if job["status"] != "completed":
        return jsonify({"search_id": job_id, "status": job["status"]})
    return jsonify({"search_id": job_id, "status": job["status"], "results": job["results"]})

async def process_entity(job_id: str, search_data: dict):
    """
    This function performs the core business logic:
    - Call Finnish Companies Registry API (PRH API)
    - Filter out inactive companies
    - For each active company, attempt to retrieve LEI data
    - Save the enriched results in the global cache
    """
    results = []
    try:
        # Use aiohttp.ClientSession to query the PRH API.
        async with aiohttp.ClientSession() as session:
            # Form external API URL using the company_name filter.
            # The API supports query parameter "name".
            params = {"name": search_data.get("company_name")}
            # TODO: Add additional filters if provided (e.g., registration_date_start/end etc.)
            async with session.get(PRH_API_BASE_URL, params=params) as response:
                if response.status != 200:
                    # Log error details as needed.
                    # TODO: handle non-200 responses in more detail.
                    entity_jobs[job_id]["status"] = "failed"
                    return
                prh_data = await response.json()
                
                # TODO: Adjust according to the actual PRH API response structure.
                companies = prh_data.get("results", [])
                
                for company in companies:
                    # Assume company contains a "status" field and "companyNames" but use a simple placeholder.
                    # Only active companies are processed.
                    if company.get("status", "").lower() != "active":
                        continue
                    
                    enriched_company = {}
                    # Map fields to output format.
                    enriched_company["company_name"] = company.get("name", "N/A")  # Assuming name field exists.
                    enriched_company["business_id"] = company.get("businessId", "N/A")
                    enriched_company["company_type"] = company.get("companyForm", "N/A")
                    enriched_company["registration_date"] = company.get("registrationDate", "N/A")
                    enriched_company["status"] = company.get("status", "N/A")
                    
                    # Retrieve LEI for the active company.
                    lei = await fetch_lei(session, enriched_company)
                    enriched_company["lei"] = lei if lei else "Not Available"

                    results.append(enriched_company)
                    
        # Save completed results in global cache.
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["results"] = results

    except Exception as e:
        # TODO: Enhance error logging.
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["results"] = {"error": str(e)}

async def fetch_lei(session: aiohttp.ClientSession, company: dict) -> str:
    """
    This function attempts to retrieve the LEI for a given company.
    Uses a placeholder logic as the LEI source is not specified.
    TODO: Replace with actual implementation when LEI service details are available.
    """
    try:
        # For the prototype, simply return a mocked LEI based on some condition.
        # This simulates the call to an external LEI service.
        # Example: if business_id ends with an even digit return a fake LEI; otherwise, not available.
        business_id = company.get("business_id", "")
        if business_id and business_id[-1] in "02468":
            # Here you could perform an async call to the actual LEI service.
            # Example:
            # params = {"business_id": business_id}
            # async with session.get(LEI_API_URL, params=params) as resp:
            #      if resp.status == 200:
            #          data = await resp.json()
            #          return data.get("lei")
            # else, use the mocked value:
            return "529900T8BM49AURSDO55"  # Mocked LEI value
        else:
            return None
    except Exception as e:
        # TODO: Handle errors in external LEI fetch properly.
        return None

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

--------------------------------------------------

This prototype covers the endpoints, business logic, and temporary persistence. It uses mocks for external calls (such as LEI data retrieval) and includes TODO comments where further information or enhancements are needed.