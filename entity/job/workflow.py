import aiohttp
import asyncio
import datetime
import uuid

# Assume these globals are defined elsewhere in your application.
# For example:
# cyoda_token = "your_token"
# ENTITY_VERSION = "v1"
# entity_service = YourEntityService()

async def fetch_company_data(params: dict):
    # Call the Finnish Companies Registry API to fetch company information.
    url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
    query_params = {"name": params.get("companyName")}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=query_params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data
                else:
                    return {"results": []}
    except Exception:
        return {"results": []}

async def fetch_lei_for_company(company: dict):
    # Fetch the Legal Entity Identifier (LEI) for a given company.
    try:
        await asyncio.sleep(0.1)  # Simulate network latency.
        if len(company.get("name", "")) % 2 == 0:
            return "529900T8BM49AURSDO55"
        else:
            return "Not Available"
    except Exception:
        return "Not Available"

async def process_fetch_company_data(entity: dict):
    # Retrieve company data and store it on the entity.
    request_data = entity.get("request_data", {})
    external_data = await fetch_company_data(request_data)
    entity["external_data"] = external_data

async def process_filter_active_companies(entity: dict):
    # Filter active companies from the external data.
    companies = entity.get("external_data", {}).get("results", [])
    active_companies = [c for c in companies if str(c.get("status", "")).lower() == "active"]
    entity["active_companies"] = active_companies

async def process_enrich_companies_with_lei(entity: dict):
    # Enrich active companies with LEI information.
    results = []
    for company in entity.get("active_companies", []):
        company_info = {
            "companyName": company.get("name"),
            "businessId": company.get("businessId"),
            "companyType": company.get("companyForm"),
            "registrationDate": company.get("registrationDate"),
            "status": "Active"
        }
        lei = await fetch_lei_for_company(company)
        company_info["LEI"] = lei
        results.append(company_info)
    entity["results"] = results

async def process_update_job_success(entity: dict):
    # Update the job record as successful.
    updated_job = {
        "job_id": entity["job_id"],
        "status": "completed",
        "results": entity.get("results", [])
    }
    await entity_service.update_item(
        token=cyoda_token,
        entity_model="job",
        entity_version=ENTITY_VERSION,
        entity=updated_job,
        meta={}
    )
    entity["updated_job"] = updated_job

async def process_update_job_failure(entity: dict):
    # Update the job record as failed. Assumes an "error" key exists on the entity.
    updated_job = {
        "job_id": entity.get("job_id"),
        "status": "failed",
        "error": entity.get("error", "Unknown error")
    }
    await entity_service.update_item(
        token=cyoda_token,
        entity_model="job",
        entity_version=ENTITY_VERSION,
        entity=updated_job,
        meta={}
    )
    entity["updated_job"] = updated_job

async def process_entity(entity: dict):
    # Core processing workflow combining all steps.
    try:
        await process_fetch_company_data(entity)
        await process_filter_active_companies(entity)
        await process_enrich_companies_with_lei(entity)
        await process_update_job_success(entity)
    except Exception as e:
        entity["error"] = str(e)
        await process_update_job_failure(entity)