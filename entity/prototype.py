from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_response
from dataclasses import dataclass
import aiohttp
import asyncio
import uuid
from datetime import datetime
import random

app = Quart(__name__)
QuartSchema(app)  # Enable QuartSchema once as required.

# Dataclass for POST request validation.
@dataclass
class CompanySearch:
    companyName: str
    page: int = 1
    # TODO: Additional filters can be added as needed.

# Dataclass for POST response validation.
@dataclass
class CompanySearchResponse:
    taskId: str
    status: str

# In-memory persistence for entity jobs.
entity_jobs = {}

# Helper function to retrieve company data from the Finnish Companies Registry API.
async def fetch_companies_data(session, company_name, page=1):
    # TODO: Expand query parameters based on additional filters if needed.
    url = f"https://avoindata.prh.fi/opendata-ytj-api/v3/companies?name={company_name}&page={page}"
    async with session.get(url) as resp:
        if resp.status != 200:
            # TODO: Handle error more gracefully.
            return None
        return await resp.json()

# Helper function to simulate LEI lookup for a given company.
async def fetch_lei(session, company):
    # TODO: Implement actual LEI data retrieval from an official source.
    await asyncio.sleep(0.1)  # Simulate network delay
    if random.choice([True, False]):
        return "MOCK-LEI-1234567890"
    else:
        return "Not Available"

# Processing task that retrieves and enriches data.
async def process_entity(job_id, task_data: dict):
    requested_at = datetime.utcnow().isoformat()
    try:
        company_name = task_data.get("companyName")
        page = task_data.get("page", 1)
        async with aiohttp.ClientSession() as session:
            companies_response = await fetch_companies_data(session, company_name, page)
            if companies_response is None:
                entity_jobs[job_id]["status"] = "failed"
                entity_jobs[job_id]["error"] = "Failed to retrieve data from Finnish Companies Registry API"
                return

            # TODO: Process companies_response based on the actual API response structure.
            companies_list = companies_response.get("results", [])
            # Filter active companies; assume each company dict has a "status" field with value "active" if active.
            active_companies = [comp for comp in companies_list if comp.get("status", "").lower() == "active"]

            enriched_results = []
            for comp in active_companies:
                lei = await fetch_lei(session, comp)
                # TODO: Map actual fields from the API response to your output model.
                enriched_results.append({
                    "companyName": comp.get("name", "Unknown"),
                    "businessId": comp.get("businessId", "Unknown"),
                    "companyType": comp.get("companyForm", "Unknown"),
                    "registrationDate": comp.get("registrationDate", "Unknown"),
                    "status": "Active",
                    "LEI": lei,
                })
            # Update job completion status.
            entity_jobs[job_id] = {
                "status": "completed",
                "data": enriched_results,
                "requestedAt": requested_at,
                "completedAt": datetime.utcnow().isoformat()
            }
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)

# Workaround for quart-schema issue: For POST methods, route decorator comes first then validation decorators.
@app.route('/companies/search', methods=['POST'])
@validate_request(CompanySearch)
@validate_response(CompanySearchResponse, 201)
async def companies_search(data: CompanySearch):
    # Create a unique job/task ID.
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, data.__dict__))
    return jsonify({"taskId": job_id, "status": "submitted"}), 201

@app.route('/companies/results/<job_id>', methods=['GET'])
async def companies_results(job_id):
    job = entity_jobs.get(job_id)
    if not job:
        abort(404, description="Task not found")
    return jsonify(job)

@app.route('/companies/results/<job_id>/status', methods=['GET'])
async def companies_status(job_id):
    job = entity_jobs.get(job_id)
    if not job:
        abort(404, description="Task not found")
    return jsonify({"taskId": job_id, "status": job.get("status")})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)

"""
Mermaid Sequence Diagram:

sequenceDiagram
    participant User as User
    participant App as Application Server
    participant PRH as Finnish Companies Registry API
    participant LEI as External LEI Service

    User->>App: POST /companies/search with JSON {companyName: "..."}
    App->>App: Validate input, generate taskId, save initial metadata
    App->>PRH: Asynchronously request company data
    PRH-->>App: Return companies data (mocked response)
    App->>App: Filter active companies
    loop For each active company
        App->>LEI: Query LEI data
        LEI-->>App: Return LEI or "Not Available" (simulated)
    end
    App->>App: Store enriched results with taskId and completedAt timestamp
    App-->>User: Response with {taskId, status: submitted}
    User->>App: GET /companies/results/{job_id}
    App-->>User: Return enriched results JSON
"""
