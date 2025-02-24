import asyncio
import aiohttp
import datetime

# This function simulates fetching the LEI for a given company.
async def process_fetch_lei_for_company(company):
    # Simulate network delay.
    await asyncio.sleep(0.1)
    if "Example" in company.get("companyName", ""):
        return "EXAMPLE-LEI-001"
    return "Not Available"

# This function calls the external API and stores the raw companies data in the entity.
async def process_call_external_api(entity):
    # Prepare API parameters from the entity.
    company_name = entity.get("companyName")
    params = {"name": company_name}
    external_api_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(external_api_url, params=params) as resp:
                if resp.status != 200:
                    entity["status"] = "error"
                    entity["results"] = {"error": f"External API returned status {resp.status}"}
                    return
                companies_data = await resp.json()
                # Store the raw companies data in the entity.
                entity["api_companies"] = companies_data.get("results", [])
    except Exception as e:
        entity["status"] = "error"
        entity["results"] = {"error": str(e)}

# This function filters active companies and enriches them with LEI codes.
async def process_enrich_companies(entity):
    companies = entity.get("api_companies", [])
    results = []
    for comp in companies:
        if comp.get("status", "").lower() != "active":
            continue
        try:
            lei_code = await process_fetch_lei_for_company(comp)
        except Exception as e:
            lei_code = f"Error: {str(e)}"
        enriched_company = {
            "companyName": comp.get("companyName", "Unknown"),
            "businessId": comp.get("businessId", "Unknown"),
            "companyType": comp.get("companyType", "Unknown"),
            "registrationDate": comp.get("registrationDate", "Unknown"),
            "status": "Active",
            "LEI": lei_code
        }
        results.append(enriched_company)
    # Store the enriched results in the entity.
    entity["enriched_results"] = results

# This function updates the entity state to completed after processing.
def process_update_entity_completed(entity):
    enriched_results = entity.get("enriched_results", [])
    entity["status"] = "completed"
    entity["results"] = enriched_results