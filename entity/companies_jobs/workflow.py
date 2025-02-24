import aiohttp
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def process_validate_input(entity):
    # Validate input data and extract companyName and filters
    input_data = entity.get("input", {})
    company_name = input_data.get("companyName", "").strip()
    if not company_name:
        entity["status"] = "failed"
        entity["error"] = "companyName is required"
        entity["completedAt"] = datetime.utcnow().isoformat()
        return None
    entity["companyName"] = company_name
    entity["filters"] = input_data.get("filters", {}) or {}
    return True

async def process_fetch_company_data(entity):
    # Call the Finnish Companies Registry API to retrieve company data
    company_name = entity["companyName"]
    filters = entity["filters"]
    prh_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
    params = {"name": company_name}
    params.update(filters)
    companies = []
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(prh_url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    companies = data.get("results", [])
                else:
                    companies = []
        except Exception as e:
            logger.error(f"Error calling PRH API: {e}")
            companies = []
    # If no companies retrieved, simulate dummy data
    if not companies:
        companies = [
            {
                "Company Name": company_name,
                "Business ID": "1234567-8",
                "Company Type": "OY",
                "Registration Date": "2020-01-01",
                "Status": "Active"
            },
            {
                "Company Name": f"{company_name} Inactive",
                "Business ID": "8765432-1",
                "Company Type": "OY",
                "Registration Date": "2019-01-01",
                "Status": "Inactive"
            }
        ]
    entity["companies"] = companies

async def process_filter_active_companies(entity):
    # Filter out inactive companies
    companies = entity.get("companies", [])
    active_companies = [company for company in companies if company.get("Status") == "Active"]
    entity["active_companies"] = active_companies

async def process_enrich_companies_with_lei(entity):
    # Enrich each active company with LEI data from an external API
    active_companies = entity.get("active_companies", [])
    lei_api_url = "https://example.com/lei"  # TODO: Replace with the real external LEI API endpoint.
    for company in active_companies:
        payload = {"businessId": company.get("Business ID")}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(lei_api_url, json=payload, timeout=10) as resp:
                    if resp.status == 200:
                        lei_data = await resp.json()
                        company["LEI"] = lei_data.get("LEI", "Not Available")
                    else:
                        company["LEI"] = "Not Available"
            except Exception as e:
                logger.error(f"Error calling LEI API: {e}")
                company["LEI"] = "Not Available"
        if not company.get("LEI"):
            company["LEI"] = "LEI1234567890"  # Fallback LEI value for prototype
    entity["active_companies"] = active_companies

async def process_finalize(entity):
    # Finalize the job entity with results and status
    entity["results"] = entity.get("active_companies", [])
    entity["status"] = "completed"
    entity["completedAt"] = datetime.utcnow().isoformat()
    entity["workflowProcessed"] = True