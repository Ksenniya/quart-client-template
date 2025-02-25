import json
import logging
import os
from pathlib import Path

from common.ai.ai_assistant_service_impl import API_V_WORKFLOWS_
from common.config.config import ENTITY_VERSION, CHAT_ID, CYODA_AI_URL, CYODA_API_URL
from common.repository.cyoda.cyoda_repository import CyodaRepository
from common.util.utils import send_post_request, send_get_request
from app_init.app_init import ai_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

cyoda_repository = CyodaRepository()
entity_dir = Path(__file__).resolve().parent.parent.parent.parent / 'entity'


async def init_cyoda(token):
    await init_entities_schema(entity_dir=entity_dir, token=token)
    #load_config_json()

async def init_entities_schema(entity_dir, token):
    for json_file in entity_dir.glob('*/**/*.json'):
        # Ensure the JSON file is in an immediate subdirectory
        if json_file.parent.parent.name != "entity" or json_file.name != 'workflow.json':
            continue

        try:
            entity_name = json_file.parent.name
            model_exists = await cyoda_repository._model_exists(token, entity_name, ENTITY_VERSION)
            if not model_exists:
                await init_workflow(entity_dir=json_file.parent, token=token, entity_name = entity_name)
        except Exception as e:
            print(f"Error reading {json_file}: {e}")
            logger.exception(e)


async def init_workflow(entity_dir, token, entity_name):
    # Traverse the directory structure
    for root, dirs, files in os.walk(entity_dir):
        # Look for 'workflow.json' files
        if 'workflow.json' in files:
            file_path = Path(root) / 'workflow.json'
            workflow_contents = file_path.read_text()
            workflow_contents = workflow_contents.replace("ENTITY_VERSION_VAR", ENTITY_VERSION)
            workflow_contents = workflow_contents.replace("ENTITY_MODEL_VAR", entity_name)
            workflow_contents = workflow_contents.replace("CHAT_ID_VAR", CHAT_ID)
            data = json.dumps({
                "workflow_json": f"{workflow_contents}",
                "class_name": "com.cyoda.tdb.model.treenode.TreeNodeEntity"
            })
            await send_post_request(token, CYODA_AI_URL, "/api/v1/workflows/initial", data)
            response = await send_post_request(token=token, api_url=CYODA_AI_URL, path="%s/return-dto" % API_V_WORKFLOWS_, data=data)
            data = response.get('json')
            response = await send_post_request(token=token, api_url=CYODA_API_URL, path="platform-api/statemachine/import?needRewrite=true", data=data)
            return response



async def init_trino(entity_name, token):
    trino_models_config = {}
    resp = await send_get_request(token=token, api_url=CYODA_API_URL, path="treeNode/model/")
    trino_models = resp.get('json')
    for model in trino_models:
        if model['modelName'] == entity_name and str(model['modelVersion']) == str(ENTITY_VERSION):
            model_details = await send_get_request(token=token, api_url=CYODA_API_URL,
                                             path=f"sql/schema/genTables/{model['id']}")
            data = {
                "id": None,
                "schemaName": entity_name,
                "tables": model_details.get('json')
            }
            resp = await send_post_request(token=token, api_url=CYODA_API_URL, path="sql/schema/", data=json.dumps(data))
            chat_id = resp.get('json')
            await ai_service.init_trino_chat(token=token, chat_id=chat_id, schema_name=entity_name)
            trino_models_config[entity_name] = chat_id
            break
    config_file_path = entity_dir / 'config.json'
    with open(config_file_path, 'w') as file:
        # Write the dictionary as JSON
        json.dump(trino_models_config, file, indent=4)

# def load_config_json():
#     config_file_path = entity_dir / 'config.json'
#     return json.loads(config_file_path.read_text())