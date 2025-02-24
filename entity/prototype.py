import asyncio
import uuid
import datetime
import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema  # Setup QuartSchema

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Mock persistence storage
entity_jobs = {}


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
                    # TODO: Adjust data parsing as per the actual API response structure
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
    The result is stored in the 'entity_jobs' cache.
    """
    company_name = request_data.get("companyName")
    if not company_name:
        entity_jobs[job_id] = {
            "status": "Failed",
            "error": "companyName is required",
            "requestedAt": datetime.datetime.utcnow().isoformat()
        }
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

    # Save the completed job
    entity_jobs[job_id] = {
        "status": "Completed",
        "companies": enriched_companies,
        "requestedAt": datetime.datetime.utcnow().isoformat()
    }


@app.route("/companies/enrich", methods=["POST"])
async def enrich_companies():
    request_data = await request.get_json()
    job_id = str(uuid.uuid4())
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.datetime.utcnow().isoformat()
    }
    # Fire and forget processing task.
    asyncio.create_task(process_entity(job_id, request_data))
    return jsonify({"jobId": job_id, "status": "processing"}), 202


@app.route("/companies/results/<job_id>", methods=["GET"])
async def get_results(job_id):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({"jobId": job_id, **job}), 200


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)