```python
import asyncio
import uuid
from datetime import datetime
from dataclasses import dataclass

from aiohttp import ClientSession
from quart import Quart, request, jsonify
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
    # Simulate network latency and return fake LEI data
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
                    error_data = {
                        "status": "error",
                        "message": "Failed to fetch company data"
                    }
                    entity_service.update_item(
                        token=cyoda_token,
                        entity_model="companies",
                        entity_version=ENTITY_VERSION,
                        entity=error_data,
                        meta={"technical_id": job_id}
                    )
                    return
                data = await response.json()
                companies_raw = data.get("results", [])
        
        active_companies = []
        for comp in companies_raw:
            if comp.get("status", "").lower() == "active":
                active_companies.append(comp)
        
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
        
        result_data = {
            "status": "completed",
            "enriched_companies": enriched_companies,
            "completedAt": datetime.utcnow().isoformat()
        }
        entity_service.update_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            entity=result_data,
            meta={"technical_id": job_id}
        )
    except Exception as e:
        error_data = {
            "status": "error",
            "message": str(e)
        }
        entity_service.update_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            entity=error_data,
            meta={"technical_id": job_id}
        )

# Workflow function applied before persisting the entity
def process_companies(entity):
    # Modify entity state if needed before persistence
    entity["workflow_executed"] = True
    entity["workflow_timestamp"] = datetime.utcnow().isoformat()
    return entity

@app.route('/companies/search', methods=['POST'])
@validate_request(CompanySearchRequest)
@validate_response(dict, 200)
async def search_companies(data: CompanySearchRequest):
    # Create an initial record in the external entity service with a processing status
    job_data = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    job_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        entity=job_data,
        workflow=process_companies  # Workflow function applied to the entity before persistence
    )
    # Fire and forget the background processing task
    asyncio.create_task(process_entity(job_id, data))
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