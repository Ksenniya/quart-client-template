import asyncio
import datetime
import aiohttp

# External API URLs
PRH_API_URL = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"  # Finnish Companies Registry API
LEI_API_URL = "https://lei.example.com/api/get"  # Placeholder for LEI lookup API

# Business logic: fetch companies from external API based on search parameters stored in entity.
async def process_fetch_companies(entity: dict):
    search_params = entity.get("searchParams", {})
    company_name = search_params.get("companyName")
    filters = search_params.get("filters", {})
    params = {"name": company_name}
    if filters:
        params.update(filters)
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(PRH_API_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    companies = data.get("results", [])
                else:
                    companies = []
        except Exception as e:
            print(f"Error fetching companies: {e}")
            companies = []
    # Save fetched companies into the entity for further processing
    entity["companies"] = companies

# Business logic: filter companies to select only those with 'active' status.
async def process_filter_active_companies(entity: dict):
    companies = entity.get("companies", [])
    active_companies = [comp for comp in companies if comp.get("status", "").lower() == "active"]
    entity["active_companies"] = active_companies

# Business logic: fetch LEI for the company stored in entity under key "current_company".
async def process_fetch_lei(entity: dict):
    current_company = entity.get("current_company", {})
    business_id = current_company.get("businessId")
    if not business_id:
        current_company["lei"] = "Not Available"
        return
    params = {"businessId": business_id}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(LEI_API_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    lei = data.get("lei", "Not Available")
                else:
                    lei = "Not Available"
        except Exception as e:
            print(f"Error fetching LEI for {business_id}: {e}")
            lei = "Not Available"
    current_company["lei"] = lei

# Business logic: enrich each active company with LEI data.
async def process_enrich_companies(entity: dict):
    active_companies = entity.get("active_companies", [])
    enriched_results = []
    for company in active_companies:
        # Set the current company in the entity as a temporary holder
        entity["current_company"] = company
        await process_fetch_lei(entity)
        enriched_company = {
            "companyName": company.get("companyName"),
            "businessId": company.get("businessId"),
            "companyType": company.get("companyType"),
            "registrationDate": company.get("registrationDate"),
            "status": "Active",
            "lei": company.get("lei")
        }
        enriched_results.append(enriched_company)
    # Save the enriched results in the entity for final persistence
    entity["enriched_results"] = enriched_results
    # Clean up temporary key
    if "current_company" in entity:
        del entity["current_company"]

# Business logic: mark the job as completed by updating entity properties.
def process_complete_job(entity: dict):
    entity["status"] = "completed"
    entity["completedAt"] = datetime.datetime.utcnow().isoformat()
    entity["results"] = entity.get("enriched_results", [])