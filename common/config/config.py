import os
import base64
from dotenv import load_dotenv
load_dotenv()  # Loads the .env file automatically
# Lambda to get an environment variable or raise an Exception if not found
get_env = lambda key: os.getenv(key) or (_ for _ in ()).throw(Exception(f"{key} not found"))

CYODA_HOST = get_env("CYODA_HOST")
CYODA_AI_URL = f"https://{CYODA_HOST}/ai"
CYODA_API_URL = f"https://{CYODA_HOST}/api"
GRPC_ADDRESS = f"grpc-{CYODA_HOST}"

decoded_bytes_cyoda_api_key = base64.b64decode(get_env("CYODA_API_KEY"))
API_KEY = decoded_bytes_cyoda_api_key.decode("utf-8")

decoded_bytes_cyoda_api_secret = base64.b64decode(get_env("CYODA_API_SECRET"))
API_SECRET = decoded_bytes_cyoda_api_secret.decode("utf-8")
CHAT_ID = os.getenv("CHAT_ID")

ENTITY_VERSION = os.getenv("ENTITY_VERSION", "1000")
GRPC_PROCESSOR_TAG = os.getenv("GRPC_PROCESSOR_TAG", CHAT_ID)

CYODA_AI_API = 'cyoda'
WORKFLOW_AI_API = 'workflow'
MOCK_AI = os.getenv("MOCK_AI", "false")
CONNECTION_AI_API = get_env("CONNECTION_AI_API")
RANDOM_AI_API = get_env("RANDOM_AI_API")
TRINO_AI_API = get_env("TRINO_AI_API")
CHAT_REPOSITORY = os.getenv("CHAT_REPOSITORY", "cyoda")
PROJECT_DIR = os.getenv("PROJECT_DIR", "/tmp")
REPOSITORY_URL = os.getenv("REPOSITORY_URL", "https://github.com/Cyoda-platform/quart-client-template")
REPOSITORY_NAME = REPOSITORY_URL.split('/')[-1].replace('.git', '')
ACCESS_TOKEN = get_env("ACCESS_TOKEN")
TEAMCITY_HOST = get_env("TEAMCITY_HOST")