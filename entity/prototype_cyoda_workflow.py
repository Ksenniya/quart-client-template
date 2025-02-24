```python
import asyncio
from datetime import datetime
from dataclasses import dataclass

from aiohttp import ClientSession
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request, validate_response

from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service
from common.config.config import ENTITY_VERSION

app = Quart(__name__)
QuartSchema(app)

PRH_API_URL = 'https://avoindata.prh.fi/opendata-ytj-api/v3/companies'

@dataclass
class CompanySearchRequest:
    company_name: str

async def fetch_lei_data(company):
    # Simulate network latency and return fake LEI data.
    await asyncio.sleep(0.1)
    business_id = company.get("business_id", "")
    return f"FAKE_LEI_{business_id}" if business_id else "Not Available"

# Workflow function applied asynchronously to the entity before persistence.
# This function encapsulates the background task previously executed via fire-and-forget.
async def process_companies(entity):
    # Ensure required attribute is present.
    company_name = entity.get("company_name")
    if not company_name:
        entity["status"] = "error"
        entity["message"] = "Missing company_name in the request data."
        entity["workflow_executed"] = True
        entity["workflow_timestamp"] = datetime.utcnow().isoformat()
        return entity
    try:
        async with ClientSession() as session:
            params = {"name": company_name}
            async with session.get(PRH_API_URL, params=params) as response:
                if response.status != 200:
                    entity["status"] = "error"
                    entity["message"] = "Failed to fetch company data from external API."
                    entity["workflow_executed"] = True
                    entity["workflow_timestamp"] = datetime.utcnow().isoformat()
                    return entity
                data = await response.json()
                companies_raw = data.get("results", [])
        # Filter only active companies.
        active_companies = [comp for comp in companies_raw if comp.get("status", "").lower() == "active"]
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
        entity["status"] = "completed"
        entity["enriched_companies"] = enriched_companies
        entity["completedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        entity["status"] = "error"
        entity["message"] = str(e)
    # Mark workflow as executed with a timestamp.
    entity["workflow_executed"] = True
    entity["workflow_timestamp"] = datetime.utcnow().isoformat()
    return entity

@app.route('/companies/search', methods=['POST'])
@validate_request(CompanySearchRequest)
@validate_response(dict, 200)
async def search_companies(data: CompanySearchRequest):
    # Prepare the initial entity data and include the request parameters required for workflow.
    job_data = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "company_name": data.company_name
    }
    # The workflow function process_companies will be applied asynchronously before persisting.
    job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        entity=job_data,
        workflow=process_companies
    )
    return jsonify({"result_id": job_id, "status": "processing"})

@app.route('/companies/results/<job_id>', methods=['GET'])
async def get_results(job_id):
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        return jsonify({"error": "Result not found"}), 404
    # Return interim status if processing is not complete.
    if job.get("status") != "completed":
        return jsonify({"result_id": job_id, "status": job.get("status")})
    return jsonify({
        "result_id": job_id,
        "companies": job.get("enriched_companies", [])
    })

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```