#!/usr/bin/env python3
import asyncio
import uuid
import datetime
import aiohttp
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response

from common.config.config import ENTITY_VERSION  # always use this constant
from app_init.app_init import cyoda_token, entity_service
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Startup: initialize cyoda repository connection.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Data model for POST /companies/enrich
@dataclass
class EnrichRequest:
    companyName: str
    registrationDateStart: str = ""
    registrationDateEnd: str = ""

# Removed local in‑memory storage; all cache interactions now use entity_service.

async def fetch_companies_from_prh(company_name: str):
    """
    Fetch companies from the Finnish Companies Registry API.
    """
    url = f"https://avoindata.prh.fi/opendata-ytj-api/v3/companies?name={company_name}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # TODO: Adjust data parsing as per the actual API response structure.
                    return data.get("results", [])
                else:
                    # TODO: Handle non-200 responses appropriately.
                    return []
        except Exception as e:
            # TODO: Add proper exception logging/handling.
            print(f"Error while fetching companies from PRH API: {e}")
            return []

async def fetch_lei_for_company(company, session: aiohttp.ClientSession):
    """
    Fetch LEI data for a given company.
    This is a placeholder for the actual LEI lookup.
    """
    business_id = company.get("businessId")
    # TODO: Replace the below URL and logic with the actual LEI lookup implementation.
    lei_url = f"https://placeholder.lei.api/lookup?businessId={business_id}"
    try:
        async with session.get(lei_url) as resp:
            if resp.status == 200:
                lei_data = await resp.json()
                # TODO: Adjust as per the structure of the LEI data source.
                lei = lei_data.get("LEI", "Not Available")
            else:
                lei = "Not Available"
    except Exception as e:
        # TODO: Add proper exception logging/handling.
        print(f"Error fetching LEI for businessId {business_id}: {e}")
        lei = "Not Available"
    return lei

async def process_entity(job_id: str, request_data: dict):
    """
    Process the data fetching and enrichment.
    The result is stored via external entity_service.
    """
    company_name = request_data.get("companyName")
    timestamp = datetime.datetime.utcnow().isoformat()
    if not company_name:
        failed_job = {
            "jobId": job_id,
            "status": "Failed",
            "error": "companyName is required",
            "requestedAt": timestamp
        }
        # Update the job status to Failed
        entity_service.update_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            entity=failed_job,
            meta={}
        )
        return

    # Fetch companies from the PRH API
    companies = await fetch_companies_from_prh(company_name)

    # Filter out inactive companies.
    # TODO: Adjust filtering criteria based on the actual API response.
    active_companies = [
        company for company in companies
        if company.get("status", "").lower() == "active"  # Assuming status field exists
    ]

    # Enrich each company with LEI data.
    enriched_companies = []
    async with aiohttp.ClientSession() as session:
        tasks = []
        for company in active_companies:
            tasks.append(fetch_lei_for_company(company, session))
        leis = await asyncio.gather(*tasks, return_exceptions=False)

    for company, lei in zip(active_companies, leis):
        company["LEI"] = lei or "Not Available"
        enriched_companies.append(company)

    completed_job = {
        "jobId": job_id,
        "status": "Completed",
        "companies": enriched_companies,
        "requestedAt": timestamp
    }
    # Update the job status to Completed with results.
    entity_service.update_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        entity=completed_job,
        meta={}
    )

@app.route("/companies/enrich", methods=["POST"])
@validate_request(EnrichRequest)  # Workaround: POST validation decorator is placed after route decorator.
@validate_response(dict, 202)
async def enrich_companies(data: EnrichRequest):
    request_data = data.__dict__
    # Generate a unique job id and prepare initial job payload.
    job_id = str(uuid.uuid4())
    timestamp = datetime.datetime.utcnow().isoformat()
    initial_job = {
        "jobId": job_id,
        "status": "processing",
        "requestedAt": timestamp
    }
    # Save initial job via external entity_service.
    added_id = entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        entity=initial_job
    )
    # Use the id returned from entity_service as the technical id.
    # Fire and forget processing task.
    asyncio.create_task(process_entity(added_id, request_data))
    return jsonify({"jobId": added_id, "status": "processing"}), 202

@app.route("/companies/results/<job_id>", methods=["GET"])
async def get_results(job_id):
    # Retrieve the job using the provided technical id.
    job = entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)