import asyncio
import aiohttp
import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

async def process_assign_technical_id(entity):
    # Ensure a technical_id is present; do not reassign if already exists.
    if "technical_id" not in entity or not entity["technical_id"]:
        entity["technical_id"] = str(uuid.uuid4())

async def process_add_timestamp(entity):
    # Add a timestamp for when the entity was added.
    entity["addedAt"] = datetime.datetime.utcnow().isoformat()

async def process_validate_company(entity):
    # Validate required field for processing.
    company_name = entity.get("companyName")
    if not company_name:
        logger.error("Missing companyName in the job entity; skipping enrichment process.")
        entity["status"] = "error"
        entity["error"] = "Missing companyName"
        return False
    return True

async def process_mark_processing(entity):
    # Immediately mark the status as processing.
    entity["status"] = "processing"

async def process_enrich_entity(entity):
    # Perform enrichment by calling external APIs.
    company_name = entity.get("companyName")
    technical_id = entity.get("technical_id")
    results = []
    registry_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
    params = {"name": company_name}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(registry_url, params=params) as resp:
                if resp.status != 200:
                    error_msg = f"Registry API returned status {resp.status}"
                    logger.error(error_msg)
                    entity["status"] = "error"
                    entity["error"] = error_msg
                    return
                registry_data = await resp.json()
        except Exception as e:
            logger.exception("Exception calling Finnish Registry API")
            entity["status"] = "error"
            entity["error"] = str(e)
            return

        companies = registry_data.get("results", [])
        logger.info("Retrieved %d companies for '%s'", len(companies), company_name)
        
        active_companies = [company for company in companies if company.get("status", "").lower() == "active"]
        logger.info("Found %d active companies", len(active_companies))
        
        lei_service_url = "https://dummy-lei-lookup.com/api/lei"
        for company in active_companies:
            lei = "Not Available"
            lookup_params = {"businessId": company.get("businessId")}
            try:
                async with session.get(lei_service_url, params=lookup_params) as lei_resp:
                    if lei_resp.status == 200:
                        lei_data = await lei_resp.json()
                        lei = lei_data.get("lei", lei)
                    else:
                        logger.warning("LEI lookup returned status %s for businessId %s", lei_resp.status, company.get("businessId"))
            except Exception as exc:
                logger.exception("Exception during LEI lookup for businessId %s", company.get("businessId"))
            enriched_company = {
                "companyName": company.get("companyName", "Unknown"),
                "businessId": company.get("businessId", "Unknown"),
                "companyType": company.get("companyType", "Unknown"),
                "registrationDate": company.get("registrationDate", "Unknown"),
                "status": company.get("status", "Unknown"),
                "lei": lei,
            }
            results.append(enriched_company)
        
        # Update the entity record with enrichment results.
        entity["status"] = "done"
        entity["completedAt"] = datetime.datetime.utcnow().isoformat()
        entity["results"] = results
        logger.info("Enrichment process completed for job %s", technical_id)