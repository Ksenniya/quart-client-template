import asyncio
import uuid
from datetime import datetime
from dataclasses import dataclass

import aiohttp
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

def process_update_requested_at(entity):
    # Update the request timestamp directly.
    entity["requestedAt"] = datetime.utcnow().isoformat()

async def process_fetch_btc_rates(entity):
    btc_api_url = "https://api.mockcrypto.com/btc_rates"
    default_rates = {"BTC_USD": 50000, "BTC_EUR": 42000}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(btc_api_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    btc_usd = data.get("BTC_USD", default_rates["BTC_USD"])
                    btc_eur = data.get("BTC_EUR", default_rates["BTC_EUR"])
                else:
                    btc_usd = default_rates["BTC_USD"]
                    btc_eur = default_rates["BTC_EUR"]
    except Exception as e:
        # Log error and continue with fallback values.
        print(f"Error fetching BTC rates: {e}")
        btc_usd = default_rates["BTC_USD"]
        btc_eur = default_rates["BTC_EUR"]
    entity["conversion_rates"] = {"BTC_USD": btc_usd, "BTC_EUR": btc_eur}

def process_send_email(entity):
    # Simulate email sending.
    entity["email_status"] = "Email sent successfully"

def process_finalize_report(entity):
    # Final update of the entity state.
    entity["timestamp"] = datetime.utcnow().isoformat()
    entity["status"] = "completed"