from common.ai.ai_assistant_service_impl import AiAssistantService
from common.auth.auth import authenticate_util
from common.config.config import CHAT_REPOSITORY
from common.repository.cyoda.cyoda_repository import CyodaRepository
from common.repository.in_memory_db import InMemoryRepository
from common.service.service import EntityServiceImpl

cyoda_token = authenticate_util()
ai_service = AiAssistantService()
if CHAT_REPOSITORY == "cyoda":
    entity_repository = CyodaRepository()
else:
    entity_repository = InMemoryRepository()
entity_service = EntityServiceImpl(entity_repository)