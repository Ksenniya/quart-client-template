import json
import logging

import aiohttp
import requests

from common.config import config
from common.config.config import CYODA_API_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def authenticate():
    login_url = f"{CYODA_API_URL}/auth/login"
    headers = {"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest"}
    auth_data = {"username": config.API_KEY, "password": config.API_SECRET}

    logger.info("Attempting to authenticate with Cyoda API.")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(login_url, headers=headers, json=auth_data, timeout=10) as response:
                if response.status == 200:
                    result = await response.json()
                    token = result.get("token")
                    logger.info("Authentication successful!")
                    return token
                else:
                    logger.error(f"Authentication failed with status {response.status}")
                    return None
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            return None



def authenticate_util():
    login_url = f"{CYODA_API_URL}/auth/login"
    headers = {"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest"}
    auth_data = {"username": config.API_KEY, "password": config.API_SECRET}

    logger.info("Attempting to authenticate with Cyoda API.")

    try:
        response = requests.post(login_url, headers=headers, data=json.dumps(auth_data), timeout=10)

        if response.status_code == 200:
            token = response.json().get("token")
            logger.info("Authentication successful!")
            return token
        else:
            logger.error(f"Authentication failed with {response}")
            return None

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return None