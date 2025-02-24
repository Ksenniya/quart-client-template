import aiohttp
import asyncio
import json

PRH_API_BASE = "https://api.prh.fi"  # Example endpoint

# Business logic function: validate that company search data has companyName.
def process_validate_company_search(entity):
    data = entity.get("companySearchData", {})
    company_name = data.get("companyName")
    if not company_name:
        entity["status"] = "failed"
        entity["error"] = "Missing companyName in search data."
    else:
        entity["_company_name"] = company_name  # store for later use
    return entity

# Business logic function: safely parse filters and store them in the entity.
def process_parse_filters(entity):
    data = entity.get("companySearchData", {})
    filters_str = data.get("filters", "")
    try:
        filters = json.loads(filters_str) if filters_str else {}
    except Exception as e:
        print("Error parsing filters:", e)
        filters = {}
    entity["_filters"] = filters
    return entity

# Business logic function: fetch companies from external API.
async def process_fetch_companies(entity):
    company_name = entity.get("_company_name")
    filters = entity.get("_filters", {})
    url = f"{PRH_API_BASE}/companies"
    params = {"name": company_name}
    params.update(filters)
    session = entity["_session"]
    try:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                entity["_companies"] = []
                return entity
            companies_data = await resp.json()
            companies = companies_data.get("companies", [])
            entity["_companies"] = companies
            return entity
    except Exception as e:
        print("Error fetching companies:", e)
        entity["_companies"] = []
        return entity

# Business logic function: filter companies that have an active status.
def process_filter_active_companies(entity):
    companies = entity.get("_companies", [])
    active_companies = [comp for comp in companies if comp.get("status", "").lower() == "active"]
    entity["_active_companies"] = active_companies
    return entity

# Business logic function: fetch LEI for a single company.
async def process_fetch_lei_for_company(entity):
    company = entity["_company_to_enrich"]
    session = entity["_session"]
    try:
        await asyncio.sleep(0.2)
    except Exception as e:
        print("Error in LEI delay:", e)
    if company.get("status", "").lower() == "active":
        return "MOCK_LEI_12345"
    return "Not Available"

# Business logic function: enrich a single company with LEI and other details.
async def process_enrich_company(entity):
    lei = await process_fetch_lei_for_company(entity)
    company = entity["_company_to_enrich"]
    enriched_company = {
        "companyName": company.get("companyName", "Unknown"),
        "businessId": company.get("businessId", "Unknown"),
        "companyType": company.get("companyType", "Unknown"),
        "registrationDate": company.get("registrationDate", "Unknown"),
        "status": "Active",
        "lei": lei
    }
    entity["_enriched_company"] = enriched_company
    return entity