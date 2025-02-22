import aiohttp
import asyncio
import datetime
from typing import Any, Dict, List

# Validate that the query parameters exist in the entity.
async def process_validate_query_params(entity: dict) -> dict:
    query_data = entity.get("queryParams", {})
    if not query_data:
        entity["status"] = "error"
        entity["results"] = {"error": "Missing query parameters"}
        entity["completedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    else:
        entity["queryData"] = query_data
    return entity

# Build the parameters for the Finnish API request based on the query data.
async def process_build_finnish_api_params(entity: dict) -> dict:
    query_data = entity.get("queryData", {})
    params = {"name": query_data.get("companyName")}
    if query_data.get("location"):
        params["location"] = query_data["location"]
    if query_data.get("registrationDateStart"):
        params["registrationDateStart"] = query_data["registrationDateStart"]
    if query_data.get("registrationDateEnd"):
        params["registrationDateEnd"] = query_data["registrationDateEnd"]
    entity["finnishParams"] = params
    return entity

# Call the Finnish API to retrieve company data.
async def process_call_finnish_api(entity: dict) -> dict:
    finnish_api_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
    session = entity.get("session")
    params = entity.get("finnishParams", {})
    async with session.get(finnish_api_url, params=params) as resp:
        if resp.status != 200:
            entity["status"] = "error"
            entity["results"] = {"error": "Failed to retrieve data from Finnish API"}
            entity["completedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
            return entity
        finnish_data = await resp.json()
        entity["finnishData"] = finnish_data
    return entity

# Filter active companies from the Finnish API response.
async def process_filter_active_companies(entity: dict) -> dict:
    finnish_data = entity.get("finnishData", {})
    companies: List[Dict[str, Any]] = finnish_data.get("results", [])
    active_companies = []
    for company in companies:
        if company.get("status", "").lower() == "active":
            active_companies.append(company)
    entity["activeCompanies"] = active_companies
    return entity

# Fetch and enrich a single company with LEI data.
async def process_fetch_and_enrich_lei(entity: dict) -> dict:
    # The entity here is a sub-entity with keys "company" and "session"
    company = entity.get("company", {})
    session = entity.get("session")
    lei_api_url = "http://example.com/lei"  # Placeholder URL; replace with actual endpoint.
    params = {"businessId": company.get("businessId")}
    try:
        async with session.get(lei_api_url, params=params) as resp:
            if resp.status == 200:
                lei_data = await resp.json()
                company["LEI"] = lei_data.get("LEI", "Not Available")
            else:
                company["LEI"] = "Not Available"
    except Exception:
        company["LEI"] = "Not Available"
    entity["company"] = company
    return entity

# Enrich all active companies with LEI information concurrently.
async def process_enrich_companies(entity: dict) -> dict:
    active_companies = entity.get("activeCompanies", [])
    session = entity.get("session")
    tasks = []
    for company in active_companies:
        # Create a sub-entity for each company containing the company and session.
        sub_entity = {"company": company, "session": session}
        tasks.append(process_fetch_and_enrich_lei(sub_entity))
    enriched_sub_entities = await asyncio.gather(*tasks)
    enriched_companies = [sub.get("company", {}) for sub in enriched_sub_entities]
    entity["enrichedCompanies"] = enriched_companies
    return entity

# Format the final results before returning.
async def process_format_results(entity: dict) -> dict:
    enriched_companies = entity.get("enrichedCompanies", [])
    results = []
    for comp in enriched_companies:
        results.append({
            "companyName": comp.get("companyName", "Unknown"),
            "businessId": comp.get("businessId", "Unknown"),
            "companyType": comp.get("companyType", "Unknown"),
            "registrationDate": comp.get("registrationDate", "Unknown"),
            "status": comp.get("status", "Unknown"),
            "LEI": comp.get("LEI", "Not Available"),
        })
    entity["results"] = results
    return entity

# Set the entity status to completed.
async def process_set_completed(entity: dict) -> dict:
    entity["status"] = "completed"
    entity["completedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    return entity