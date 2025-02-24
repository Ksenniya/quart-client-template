import asyncio
import datetime
import json
import aiohttp

# process_fetch_conversion_rates fetches Bitcoin conversion rates and updates the entity.
async def process_fetch_conversion_rates(entity):
    url = "https://api.coindesk.com/v1/bpi/currentprice/BTC.json"  # Placeholder API endpoint
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    # Mark entity as failed if the API response is not successful.
                    entity["status"] = "failed"
                    entity["error"] = f"Received status code {resp.status} from conversion rates API"
                    return
                data = await resp.json()
    except Exception as ex:
        entity["status"] = "failed"
        entity["error"] = f"Exception fetching conversion rates: {ex}"
        return

    try:
        rates = {
            "BTC_USD": data["bpi"]["USD"]["rate_float"],
            "BTC_EUR": data["bpi"]["EUR"]["rate_float"]
        }
    except (KeyError, TypeError) as ex:
        rates = {"BTC_USD": None, "BTC_EUR": None}
        entity["status"] = "failed"
        entity["error"] = f"Error parsing conversion rates: {ex}"
        return

    entity["rates"] = rates

# process_build_report_details builds report details from the entity data.
async def process_build_report_details(entity):
    # Build report details using job_id from the entity and the fetched conversion rates.
    report_details = {
        "report_id": entity.get("job_id", "unknown"),
        "rates": entity.get("rates"),
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    # Store the report details in the entity.
    entity["report_details"] = report_details

# process_send_email sends an email with the report details and updates the entity.
async def process_send_email(entity):
    async def send_email(report):
        try:
            await asyncio.sleep(0.5)  # Simulate network delay
            print(f"Email sent with report: {json.dumps(report)}")
            return "sent"
        except Exception as ex:
            print(f"Error in send_email: {ex}")
            return "failed"

    # Retrieve the report details from the entity.
    report = entity.get("report_details", {})
    email_status = await send_email(report)
    # Update report details with email status and mark the report as completed.
    report["email_status"] = email_status
    report["status"] = "completed"
    # Merge report details into the main entity.
    entity.update(report)