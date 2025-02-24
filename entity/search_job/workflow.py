import aiohttp
import asyncio
import logging
from datetime import datetime

PRH_API_URL = "https://api.example.com/companies"  # Example URL

async def process_build_params(entity):
    # Build query parameters for the PRH API based on search criteria.
    criteria = entity.get("criteria", {})
    params = {"name": criteria.get("companyName", "")}
    if criteria.get("location"):
        params["location"] = criteria["location"]
    if criteria.get("businessId"):
        params["businessId"] = criteria["businessId"]
    if criteria.get("companyForm"):
        params["companyForm"] = criteria["companyForm"]
    if criteria.get("registrationDateStart"):
        params["registrationDateStart"] = criteria["registrationDateStart"]
    if criteria.get("registrationDateEnd"):
        params["registrationDateEnd"] = criteria["registrationDateEnd"]
    entity["params"] = params

async def process_fetch_companies(entity):
    # Use the session stored in entity to call the PRH API.
    session = entity["_session"]
    params = entity.get("params", {})
    async with session.get(PRH_API_URL, params=params) as resp:
        if resp.status != 200:
            companies_data = {"results": []}
        else:
            companies_data = await resp.json()
    entity["companies_data"] = companies_data

async def process_filter_active_companies(entity):
    # Filter companies with active status.
    companies_data = entity.get("companies_data", {})
    active_companies = []
    for company in companies_data.get("results", []):
        if company.get("status", "").lower() == "active":
            active_companies.append(company)
    entity["active_companies"] = active_companies

async def process_fetch_lei(entity):
    # Fetch the LEI data for a company.
    try:
        # Simulate network delay for LEI lookup.
        await asyncio.sleep(0.1)
        company = entity.get("_current_company", {})
        business_id = company.get("businessId", "")
        if business_id and business_id[-1] in "02468":
            return "5493001KJTIIGC8Y1R12"  # Example LEI
    except Exception as e:
        logging.exception("Error fetching LEI")
    return None

async def process_enrich_companies(entity):
    # Enrich the active companies with LEI data.
    session = entity["_session"]  # Ensure session is available in the entity.
    active_companies = entity.get("active_companies", [])
    enriched = []
    for comp in active_companies:
        # Use a temporary key to pass the company to process_fetch_lei.
        entity["_current_company"] = comp
        lei = await process_fetch_lei(entity)
        enriched.append({
            "companyName": comp.get("name", "Unknown"),
            "businessId": comp.get("businessId", "Unknown"),
            "companyType": comp.get("companyType", "Unknown"),  # TODO: Verify actual field name if needed.
            "registrationDate": comp.get("registrationDate", "Unknown"),
            "status": "Active",
            "LEI": lei if lei else "Not Available"
        })
        # Remove temporary key after processing each company.
        entity.pop("_current_company", None)
    entity["enriched_companies"] = enriched

async def process_set_result(entity):
    # Build final result and update entity state.
    result = {
        "searchId": entity.get("id"),
        "retrievedAt": datetime.utcnow().isoformat() + "Z",
        "companies": entity.get("enriched_companies", [])
    }
    entity["result"] = result
    entity["status"] = "completed"
    entity["workflowProcessedAt"] = datetime.utcnow().isoformat() + "Z"