```python
import asyncio
import uuid
from datetime import datetime
from dataclasses import dataclass

from aiohttp import ClientSession
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response  # Workaround: For POST, route is declared first then validations.

app = Quart(__name__)
QuartSchema(app)

# In-memory cache to mock persistence
job_cache = {}

# External API endpoint for Finnish Companies Registry
PRH_API_URL = 'https://avoindata.prh.fi/opendata-ytj-api/v3/companies'

@dataclass
class CompanySearchRequest:
    company_name: str

# TODO: Additional fields from company search request can be added as needed.

async def fetch_lei_data(company):
    # TODO: Replace with a call to an official LEI registry or reliable financial data source.
    # This is a placeholder that simulates network latency.
    await asyncio.sleep(0.1)
    business_id = company.get("business_id", "")
    return f"FAKE_LEI_{business_id}" if business_id else "Not Available"

async def process_entity(job_id, input_data: CompanySearchRequest):
    """Background task to query the Finnish Companies Registry API, filter and enrich company data."""
    try:
        async with ClientSession() as session:
            params = {"name": input_data.company_name}
            async with session.get(PRH_API_URL, params=params) as response:
                if response.status != 200:
                    job_cache[job_id] = {
                        "status": "error",
                        "message": "Failed to fetch company data"
                    }
                    return
                data = await response.json()
                # TODO: Adapt to the actual response structure from the Finnish Companies Registry API.
                companies_raw = data.get("results", [])
        
        # Filter out inactive companies
        active_companies = []
        for comp in companies_raw:
            # TODO: Confirm which field indicates the company's active status.
            # For now, assume comp["status"] is available and equals "active" for active companies.
            if comp.get("status", "").lower() == "active":
                active_companies.append(comp)
        
        # Enrich each active company with LEI data
        enriched_companies = []
        for company in active_companies:
            lei = await fetch_lei_data(company)
            enriched_company = {
                "company_name": company.get("name", "Unknown"),
                "business_id": company.get("business_id", "Unknown"),
                "company_type": company.get("company_form", "Unknown"),
                "registration_date": company.get("registration_date", "Unknown"),
                "status": "Active",
                "lei": lei
            }
            enriched_companies.append(enriched_company)
        
        # Store the results in the cache
        job_cache[job_id] = {
            "status": "completed",
            "enriched_companies": enriched_companies,
            "completedAt": datetime.utcnow().isoformat()
        }
    except Exception as e:
        job_cache[job_id] = {
            "status": "error",
            "message": str(e)
        }

@app.route('/companies/search', methods=['POST'])
@validate_request(CompanySearchRequest)  # Workaround: Validation decorators for POST are applied after the route decorator.
@validate_response(dict, 200)
async def search_companies(data: CompanySearchRequest):
    # Generate a unique job id
    job_id = str(uuid.uuid4())
    job_cache[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, data))
    
    return jsonify({"result_id": job_id, "status": "processing"})

@app.route('/companies/results/<job_id>', methods=['GET'])
async def get_results(job_id):
    job = job_cache.get(job_id)
    if not job:
        return jsonify({"error": "Result not found"}), 404
    
    if job.get("status") != "completed":
        return jsonify({"result_id": job_id, "status": job.get("status")})
    
    return jsonify({
        "result_id": job_id,
        "companies": job.get("enriched_companies", [])
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```