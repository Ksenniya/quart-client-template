import json
import logging

import httpx
import requests

from common.config import config
from common.config.config import CYODA_API_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def authenticate():
    login_url = f"{CYODA_API_URL}/auth/login"
    headers = {"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest"}
    auth_data = {"username": config.API_KEY, "password": config.API_SECRET}

    logger.info(f"Attempting to authenticate with Cyoda API., login url: {login_url}")

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.post(login_url, headers=headers, json=auth_data)
            if response.status_code == 200:
                result = response.json()
                token = result.get("token")
                logger.info("Authentication successful!")
                return token
            else:
                logger.error(f"Authentication failed with status {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            return None


def authenticate_util():
    login_url = f"{CYODA_API_URL}/auth/login"
    headers = {"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest"}
    auth_data = {"username": config.API_KEY, "password": config.API_SECRET}

    logger.info(f"Attempting to authenticate with Cyoda API., login url: {login_url}")

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