import json
import logging

from common.ai.ai_assistant_service import IAiAssistantService
from common.config.config import CYODA_AI_URL, CYODA_AI_API, WORKFLOW_AI_API, CONNECTION_AI_API, RANDOM_AI_API, MOCK_AI, \
    TRINO_AI_API
from common.util.utils import parse_json, validate_result, send_post_request, ValidationErrorException

API_V_CONNECTIONS_ = "api/v1/connections"
API_V_CYODA_ = "api/v1/cyoda"
API_V_WORKFLOWS_ = "api/v1/workflows"
API_V_RANDOM_ = "api/v1/random"
API_V_TRINO_ = "api/v1/trino"

logger = logging.getLogger(__name__)

from openai import OpenAI
client = OpenAI()
class OpenAiAssistantService(IAiAssistantService):
    def __init__(self):
        pass

    async def init_chat(self, token, chat_id):

        return {"success": True}

    async def init_workflow_chat(self, token, chat_id):
        return {"success": True}

    async def init_connections_chat(self, token, chat_id):
        return {"success": True}

    async def init_random_chat(self, token, chat_id):
        return {"success": True}

    async def init_cyoda_chat(self, token, chat_id):
        return {"success": True}

    async def init_trino_chat(self, token, chat_id, schema_name):
        return {"success": True}


    async def ai_chat(self, token, chat_id, ai_endpoint, ai_question):
        if ai_question and len(str(ai_question).encode('utf-8')) > 1 * 1024 * 1024:
            return {"error": "Answer size exceeds 1MB limit"}
        if MOCK_AI=="true":
            return {"entity": "some random text"}
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                {"role": "system", "content": "You are Cyoda app builder."},
                {
                    "role": "user",
                    "content": ai_question
                }
            }],
            conversation_id=chat_id
        )
        resp = completion.choices[0].message
        logger.info(resp)
        return resp


