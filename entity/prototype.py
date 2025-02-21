Below is an example prototype.py file implementing a basic Quart application. This prototype uses aiohttp.ClientSession for external HTTP requests and a local in‑memory cache for persistence. Note that external API calls and persistence are simplified with mocks and TODO comments for missing details.

--------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
from datetime import datetime

from quart import Quart, request, jsonify
from quart_schema import QuartSchema  # single-line integration per instructions
import aiohttp

app = Quart(__name__)
QuartSchema(app)

# In‑memory cache for jobs
jobs = {}  # Example structure: {job_id: {"status": "processing"/"completed", "requestedAt": ..., "result": ...}}

# -------------------------------
# Helper Functions

async def fetch_company_data(company_name: str, filters: dict) -> list:
    """
    Query the Finnish Companies Registry API using aiohttp.
    For now, only query by company name is implemented.
    TODO: Incorporate additional filters and error handling as necessary.
    """
    url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
    params = {"name": company_name}
    # TODO: Add additional parameters from filters if provided
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            # This prototype expects JSON response. 
            # TODO: validate structure and handle errors.
            data = await response.json()
            # Assuming data structure contains a key 'results' with list of companies.
            return data.get("results", [])

async def fetch_lei(company: dict) -> str:
    """
    Fetch the Legal Entity Identifier (LEI) for a given company.
    This is a placeholder function and uses a mock.
    TODO: Integrate with an official LEI API or other reliable source.
    """
    # Simulate network delay.
    await asyncio.sleep(0.1)
    # For demonstration, if the companyName length is even, return a fake LEI.
    if len(company.get("companyName", "")) % 2 == 0:
        return "FAKELEI1234567890"
    else:
        return "Not Available"

def filter_active_companies(companies: list) -> list:
    """
    Filter the companies retrieving only active companies.
    Here we assume that the company dictionary includes a 'businessStatus' field.
    TODO: Adjust filter logic per actual response structure.
    """
    active_companies = []
    for company in companies:
        # TODO: Update condition based on actual API field name and valid values.
        if company.get("businessStatus", "").lower() == "active":
            active_companies.append(company)
    return active_companies

async def process_search(job_id: str, payload: dict):
    """
    Background task to process search:
      1. Query external companies API.
      2. Filter out inactive companies.
      3. Enrich each active company with LEI information.
      4. Store the result in the jobs cache.
    """
    try:
        company_name = payload.get("companyName", "")
        filters = payload.get("filters", {})

        # Step 1: Retrieve data from Finnish Companies Registry API.
        companies = await fetch_company_data(company_name, filters)
        
        # Step 2: Filter out inactive companies.
        active_companies = filter_active_companies(companies)
        
        # Step 3: Enrich with LEI.
        enriched_companies = []
        for company in active_companies:
            lei = await fetch_lei(company)
            # Build the final company model.
            enriched_company = {
                "companyName": company.get("companyName", "Unknown"),
                "businessId": company.get("businessId", "Unknown"),
                "companyType": company.get("companyForm", "Unknown"),
                "registrationDate": company.get("registrationDate", "Unknown"),
                "status": "Active",  # since we filtered to active companies.
                "lei": lei
            }
            enriched_companies.append(enriched_company)
        
        # Optional: simulate some processing delay
        await asyncio.sleep(0.1)
        
        # Step 4: Store result in our local cache.
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = {
            "searchId": job_id,
            "companies": enriched_companies
        }
    except Exception as e:
        # TODO: Better error management and logging.
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
    

# -------------------------------
# API Endpoints

@app.route('/companies/search', methods=['POST'])
async def post_company_search():
    """
    Accepts search criteria, triggers external API calls and enrichment.
    Uses POST since business logic involves external data retrieval and calculations.
    """
    payload = await request.get_json()
    if not payload or "companyName" not in payload:
        return jsonify({"error": "Missing required field: companyName"}), 400

    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()
    
    # Store initial job details in local cache.
    jobs[job_id] = {"status": "processing", "requestedAt": requested_at}
    
    # Fire and forget the processing task.
    asyncio.create_task(process_search(job_id, payload))
    
    # Return the search ID and a message.
    return jsonify({
        "searchId": job_id,
        "status": "processing",
        "requestedAt": requested_at
    }), 202

@app.route('/companies/results', methods=['GET'])
async def get_company_results():
    """
    Retrieves stored search results.
    Query parameters:
      - searchId: identifier for the search job.
      - format (optional): json (default) or csv.
    """
    search_id = request.args.get("searchId")
    output_format = request.args.get("format", "json").lower()
    if not search_id:
        return jsonify({"error": "Missing searchId query parameter"}), 400

    # Check if job exists.
    job = jobs.get(search_id)
    if job is None:
        return jsonify({"error": "Invalid searchId"}), 404

    # If processing not complete, return status.
    if job["status"] != "completed":
        return jsonify({"searchId": search_id, "status": job["status"]}), 202

    result = job.get("result", {})
    
    # Handle CSV output if requested. This is a simple conversion.
    if output_format == "csv":
        from io import StringIO
        import csv
        si = StringIO()
        cw = csv.writer(si)
        # Write headers.
        headers = ["companyName", "businessId", "companyType", "registrationDate", "status", "lei"]
        cw.writerow(headers)
        for company in result.get("companies", []):
            cw.writerow([
                company.get("companyName"),
                company.get("businessId"),
                company.get("companyType"),
                company.get("registrationDate"),
                company.get("status"),
                company.get("lei")
            ])
        response = app.response_class(si.getvalue(), mimetype='text/csv')
        return response

    # Default JSON output.
    return jsonify(result), 200

# -------------------------------
# Mermaid Diagram Representation (for documentation purposes)
mermaid_diagram = """
sequenceDiagram
    participant Client as Client App
    participant API as Backend API
    participant PRH as Finnish Companies Registry API
    participant LEI as External LEI Service
    participant Cache as Local Job Cache

    Client->>API: POST /companies/search {companyName, filters...}
    API->>Cache: Create job with searchId, status "processing"
    API->>PRH: Request company data based on criteria
    PRH-->>API: Return company data
    API->>API: Filter inactive companies
    loop For each active company
      API->>LEI: Request LEI details
      LEI-->>API: Return LEI or "Not Available"
    end
    API->>Cache: Update job status to "completed" with results
    API-->>Client: Return searchId and status (processing)
    Client->>API: GET /companies/results?searchId=xxx&format=json
    API->>Cache: Retrieve stored result for searchId
    API-->>Client: Return final search result (JSON or CSV)
"""

# Entry point
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

--------------------------------------------------

This code should serve as a working prototype for verifying the UX and identifying any requirement gaps. Adjustments and detailed error handling can be added in future iterations when the full requirements are clarified.