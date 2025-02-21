async def process_companies_workflow(entity: dict):
    # The search term is stored in the entity under "searchTerm"
    search_term = entity.get("searchTerm", "")
    if not search_term:
        entity["status"] = "failed"
        entity["error"] = "Search term is missing."
        return entity

    async with aiohttp.ClientSession() as session:
        try:
            # Build URL for the Finnish Companies Registry API.
            base_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
            url = f"{base_url}?name={search_term}"
            async with session.get(url) as resp:
                if resp.status != 200:
                    # If external API returns error status, log error and update entity.
                    entity["status"] = "failed"
                    entity["error"] = f"External company API returned status: {resp.status}"
                    return entity
                companies_data = await resp.json()
        except Exception as e:
            entity["status"] = "failed"
            entity["error"] = f"Exception during company API call: {str(e)}"
            return entity

        # Process and enrich the results retrieved.
        results = []
        for company in companies_data.get("results", []):
            # Filter out companies that are not active.
            if company.get("status", "").lower() != "active":
                continue

            business_id = company.get("businessId", "")
            lei_url = f"https://mock-lei-api.com/api/lei?businessId={business_id}"  # TODO: Replace with a proper endpoint

            try:
                async with session.get(lei_url) as lei_resp:
                    if lei_resp.status == 200:
                        lei_data = await lei_resp.json()
                        company["lei"] = lei_data.get("lei", "Not Available")
                    else:
                        company["lei"] = "Not Available"
            except Exception:
                # In case of an error while retrieving LEI information
                company["lei"] = "Not Available"

            # Append the enriched result with a safe default in case of missing keys.
            results.append({
                "companyName": company.get("companyName", "Unknown"),
                "businessId": business_id,
                "companyType": company.get("companyType", "Unknown"),
                "registrationDate": company.get("registrationDate", "Unknown"),
                "status": "Active",
                "lei": company.get("lei", "Not Available")
            })

        # If no active companies were found, mark the job as completed with an empty result.
        entity["results"] = results
        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat()
        # Mark that the workflow processed this entity.
        entity["workflowApplied"] = True

    return entity