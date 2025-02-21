Below is an example prototype.py that implements the design as specified. Note that external API calls are made using aiohttp.ClientSession, persistence is mocked with a local in‑memory dictionary, and any ambiguous behavior (such as the structure of the external API responses) is marked with TODO comments.

------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
from datetime import datetime
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # one-line integration of QuartSchema

# In‑memory persistence cache for demonstration only.
entity_jobs = {}  # key: job_id, value: job details

# ------------------------------
# Asynchronous processing task
# ------------------------------
async def process_entity(job: dict, request_data: dict):
    # Create an aiohttp session for external calls
    async with aiohttp.ClientSession() as session:
        try:
            # Build URL for the Finnish Companies Registry API using the provided company name.
            base_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
            # TODO: Expand URL building if additional filters are provided in request_data["additionalFilters"]
            name = request_data.get("name", "")
            url = f"{base_url}?name={name}"
            
            async with session.get(url) as resp:
                # TODO: Adapt handling if the external API returns non-200 codes.
                companies_data = await resp.json()
        except Exception as e:
            job["status"] = "failed"
            job["error"] = f"Error retrieving companies: {str(e)}"
            return

        # Prepare list to store enriched company data.
        results = []
        # TODO: Adjust key names based on actual API response schema.
        for company in companies_data.get("results", []):
            # Filter: Only consider companies marked as active.
            # TODO: Adjust the condition based on the actual field defining active/inactive status.
            if company.get("status", "").lower() != "active":
                continue

            # Fetch LEI data for each active company.
            business_id = company.get("businessId", "")
            lei_url = f"https://mock-lei-api.com/api/lei?businessId={business_id}"  # Placeholder URL

            try:
                async with session.get(lei_url) as lei_resp:
                    if lei_resp.status == 200:
                        lei_data = await lei_resp.json()
                        # TODO: Adjust based on actual response structure from the LEI API.
                        company["lei"] = lei_data.get("lei", "Not Available")
                    else:
                        company["lei"] = "Not Available"
            except Exception:
                company["lei"] = "Not Available"  # In case of errors, mark as not available

            results.append({
                "companyName": company.get("companyName", "Unknown"),
                "businessId": business_id,
                "companyType": company.get("companyType", "Unknown"),
                "registrationDate": company.get("registrationDate", "Unknown"),
                "status": "Active",
                "lei": company.get("lei")
            })

        # Save the processing result in our in-memory job.
        job["results"] = results
        job["status"] = "completed"
        job["completedAt"] = datetime.utcnow().isoformat()

# ------------------------------
# POST Endpoint: Trigger data processing and enrichment.
# ------------------------------
@app.route('/companies/search', methods=['POST'])
async def search_companies():
    request_data = await request.get_json()
    if not request_data or "name" not in request_data:
        # Input validation minimal since data is dynamic.
        return jsonify({"error": "missing required field 'name'"}), 400

    # Create a unique job id and mark the job as processing.
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at, "results": []}

    # Fire-and-forget background processing task.
    # Using create_task so that the POST returns immediately.
    asyncio.create_task(process_entity(entity_jobs[job_id], request_data))

    # Return the job details (identifier and status)
    return jsonify({"searchId": job_id, "status": "processing"})

# ------------------------------
# GET Endpoint: Retrieve processed results.
# ------------------------------
@app.route('/companies/result/<string:search_id>', methods=['GET'])
async def get_companies_result(search_id):
    job = entity_jobs.get(search_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    # Basic pagination parameters.
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("pageSize", 100))
    except ValueError:
        return jsonify({"error": "Invalid pagination parameters"}), 400

    results = job.get("results", [])
    total_results = len(results)
    total_pages = (total_results + page_size - 1) // page_size

    # Slicing the result for the current page.
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    paginated_results = results[start_index:end_index]

    return jsonify({
        "searchId": search_id,
        "results": paginated_results,
        "pagination": {
            "currentPage": page,
            "pageSize": page_size,
            "totalPages": total_pages,
            "totalResults": total_results
        },
        "status": job.get("status")
    })

# ------------------------------
# Entry point
# ------------------------------
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

------------------------------------------------

Notes:
• External API calls are implemented using aiohttp.ClientSession. Adjust URL parameters and response handling based on the actual APIs.
• Persistence is implemented as an in‑memory dictionary (entity_jobs). This is solely for demonstration.
• TODO comments indicate areas where integration with real external data and more precise filtering logic is needed.
• The processing task uses asyncio.create_task to fire and forget the enrichment process so that the POST endpoint returns quickly, enabling UX testing of asynchronous behavior.