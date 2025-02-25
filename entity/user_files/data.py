import copy

from common.ai.ai_assistant_service import OPEN_AI, OPEN_AI, OPEN_AI_o3
from common.config.config import MAX_ITERATION
from common.config.conts import EMPTY_PROMPT

APP_BUILDING_STACK_KEY = "app_building_stack"

DATA_INGESTION_STACK_KEY = "data_ingestion_stack"

ENTITY_STACK_KEY = "entity_stack"

WORKFLOW_STACK_KEY = "workflow_stack"

PROCESSORS_STACK_KEY = "processors_stack"

SCHEDULER_STACK_KEY = "scheduler_stack"

FORM_SUBMISSION_STACK_KEY = "form_submission_stack"

FILE_UPLOAD_STACK_KEY = "file_upload_stack"

API_REQUEST_STACK_KEY = "api_request_stack"
APPROVAL_NOTIFICATION = "Give a thumbs up 👍 if you'd like to proceed to the next question. If you'd like to discuss further, let's chat 💬"
DESIGN_PLEASE_WAIT = "Please give me a moment to think everything over 🤔⏳"
APPROVE_WARNING = "Sorry, you cannot skip this question. If you're unsure about anything, please refer to the example answers for guidance. If you need further help, just let us know! 😊 Apologies for the inconvenience!🙌"
OPERATION_FAILED_WARNING = "⚠️ Sorry, this action is not available right now. Please try again or wait for new questions ⚠️"
OPERATION_NOT_SUPPORTED_WARNING = "⚠️ Sorry, this operation is not supported ⚠️"
DESIGN_IN_PROGRESS_WARNING = "Sorry, you cannot submit answer right now. We are working on Cyoda design. Could you please wait a little"
DESIGN_IN_PROGRESS_ROLLBACK_WARNING = "Sorry, you cannot rollback right now. We are working on Cyoda design. Could you please wait a little"
ADDITIONAL_QUESTION_ROLLBACK_WARNING = "Sorry, this is an additional question, you cannot rollback to it. Please rollback to the earlier question"
BRANCH_READY_NOTIFICATION = """🎉 **Your branch is ready!** Please update the project and check it out when you get a chance. 😊

To get started:

1. **Clone the repository** using the following command:  
   `git clone https://github.com/Cyoda-platform/quart-client-template/` 🚀

2. **Checkout your branch** using:  
   `git checkout {chat_id}` 🔄

You can access your branch directly on GitHub here: [Cyoda Platform GitHub](https://github.com/Cyoda-platform/quart-client-template/tree/{chat_id}) 😄

This repository is a **starter template** for your app and has two main modules:

- **Common Module**: This is all about integration with Cyoda! You don’t need to edit it unless you want to – it’s all done for you! 🎉  
- **Entity Module**: This is where your business logic and custom files will go. We'll add your files here, and you can track your progress. 📈 Feel free to **add or edit** anything in the Entity module. I’ll be pulling changes now and then, so just push your updates to let me know! 🚀

You can ask **questions in the chat** or in your project files anytime. When I make changes, I’ll let you know, and you can simply **pull** to sync with me! 🔄💬

Happy coding! 😄🎉"""

PUSHED_CHANGES_NOTIFICATION = """

🎉 **Changes have been pushed!** 🎉

I’ve submitted changes to the file: `{file_name}` in your branch. You can check it out by either:

1. **Pulling or fetching** the changes from the remote repository, or  
2. **Opening the link** to view the file directly: [View changes here]( {repository_url}/tree/{chat_id}/{file_name}) 🔗 (this will open in a new tab).

Feel free to **modify the file** as necessary

I will proceed with my work... I'll let you know when we can discuss the changes and make necessary update.
"""

FILES_NOTIFICATIONS = {
    "code": {
        "text": "🖌️💬",
        "file_name": "entity/{entity_name}/connections/connections.py"},
    "doc": {
        "text": "😊 Could you please provide more details for the connection documentation? It would be super helpful! Please provide raw data for each endpoint if the final entity structure is different. You can paste all your data right here. Thanks so much!",
        "file_name": "entity/{entity_name}/connections/connections_input.md"},
    "entity": {
        "text": "😊 Could you please provide an example of the entity JSON? It will help us map the raw data to the entity or save the raw data as is. You can paste all your data right here. Thanks a lot!",
        "file_name": "entity/{entity_name}/{entity_name}.json"}
}

LOGIC_CODE_DESIGN_STR = "Additional logic code design"

WORKFLOW_CODE_DESIGN_STR = "Workflow processors code design"

WORKFLOW_DESIGN_STR = "Workflow design"

ENTITIES_DESIGN_STR = "Entities design"

APPLICATION_DESIGN_STR = "Application design"

GATHERING_REQUIREMENTS_STR = "Gathering requirements"

QUESTION_OR_VALIDATE = "Could you please help me review my output and approve it you are happy with the result 😸"

APP_BUILDER_FLOW = [
    {GATHERING_REQUIREMENTS_STR: "Let's collect all the necessary details."},
    {
        APPLICATION_DESIGN_STR: "Let's design the application using diagrams and chat. You'll receive a text document with the PRD as the output. Output documents: entity/app_design.json"},
    {ENTITIES_DESIGN_STR: "Let's define the JSON data structure for each entity."},
    {WORKFLOW_DESIGN_STR: "Let's ensure our entity workflow is correctly defined."},
    {WORKFLOW_CODE_DESIGN_STR: "Let's implement the workflow processors."},
    {LOGIC_CODE_DESIGN_STR: "Let's develop any additional business logic."}
]
ENTITY_DESIGN_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Generated schema for Root",
    "type": "object",
    "properties": {
        "primary_entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "entity_name": {
                        "type": "string"
                    },
                    "endpoints": {
                        "type": "object",
                        "properties": {
                            "POST": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "endpoint": {
                                            "type": "string"
                                        },
                                        "description": {
                                            "type": "string"
                                        },
                                        "suggested_workflow": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "start_state": {
                                                        "type": "string"
                                                    },
                                                    "end_state": {
                                                        "type": "string"
                                                    },
                                                    "action": {
                                                        "type": "string"
                                                    },
                                                    "complete_code_for_action_derived_from_the_prototype": {
                                                        "type": "string"
                                                    },
                                                    "description": {
                                                        "type": "string"
                                                    },
                                                    "related_secondary_entities": {
                                                        "type": "array",
                                                        "items": {}
                                                    }
                                                },
                                                "required": [
                                                    "start_state",
                                                    "end_state",
                                                    "description",
                                                ]
                                            }
                                        }
                                    },
                                    "required": [
                                        "endpoint",
                                        "description",
                                        "suggested_workflow"
                                    ]
                                }
                            },
                            "GET": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "endpoint": {
                                            "type": "string"
                                        },
                                        "description": {
                                            "type": "string"
                                        }
                                    },
                                    "required": [
                                        "endpoint",
                                        "description"
                                    ]
                                }
                            }
                        },
                        "required": [
                            "POST",
                            "GET"
                        ]
                    }
                },
                "required": [
                    "entity_name",
                    "endpoints"
                ]
            }
        },
        "secondary_entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "entity_name": {
                        "type": "string"
                    },
                    "endpoints": {
                        "type": "object",
                        "properties": {
                            "GET": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "endpoint": {
                                            "type": "string"
                                        },
                                        "description": {
                                            "type": "string"
                                        }
                                    },
                                    "required": [
                                        "endpoint",
                                        "description"
                                    ]
                                }
                            }
                        },
                        "required": [
                            "GET"
                        ]
                    }
                },
                "required": [
                    "entity_name",
                    "endpoints"
                ]
            }
        }
    },
    "required": [
        "primary_entities",
        "secondary_entities"
    ]
}
ENTITY_WORKFLOW = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string"
        },
        "class_name": {
            "type": "string",
            "enum": ["com.cyoda.tdb.model.treenode.TreeNodeEntity"]
        },
        "transitions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string"
                    },
                    "description": {
                        "type": "string"
                    },
                    "start_state": {
                        "type": "string"
                    },
                    "start_state_description": {
                        "type": "string"
                    },
                    "end_state": {
                        "type": "string"
                    },
                    "end_state_description": {
                        "type": "string"
                    },
                    # "criteria": {
                    #     "type": "object",
                    #     "properties": {
                    #         "name": {
                    #             "type": "string"
                    #         },
                    #         "description": {
                    #             "type": "string"
                    #         }
                    #     },
                    #     "required": [
                    #         "name",
                    #         "description"
                    #     ]
                    # },
                    "process": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string"
                            },
                            "description": {
                                "type": "string"
                            },
                            "adds_new_entites": {
                                "type": "string"
                            }
                        },
                        "required": [
                            "name",
                            "description",
                            "adds_new_entites"
                        ]
                    }
                },
                "required": [
                    "name",
                    "start_state",
                    "end_state",
                    "process"
                ]
            }
        }
    },
    "required": [
        "name",
        "class_name",
        "transitions"
    ]
}

# Finished
app_building_stack = [{"question": None,
                       "prompt": {
                           "text": EMPTY_PROMPT,
                           "api": {"model": OPEN_AI, "temperature": 0.7},
                       },
                       "answer": None,
                       "approve": False,
                       "function": None,
                       "iteration": 0,
                       "flow_step": GATHERING_REQUIREMENTS_STR,
                       "max_iteration": MAX_ITERATION * 10,
                       "additional_questions": [
                           {
                               "question": "Feel free to ask any questions or discuss the design in the chat 💬💬",
                               "approve": True}],
                       "stack": APP_BUILDING_STACK_KEY,
                       "publish": True},
                      {"question": "Your application is finished! Thank you for collaboration!",
                       "prompt": {},
                       "answer": None,
                       "function": None,
                       "index": 2,
                       "iteration": 0,
                       "file_name": "entity/chat.json",
                       "max_iteration": 0,
                       "stack": APP_BUILDING_STACK_KEY,
                       "publish": True},
                      {"question": None,
                       "prompt": {},
                       "answer": None,
                       "function": {"name": "save_env_file"},
                       "index": 2,
                       "iteration": 0,
                       "file_name": ".env.template",
                       "notification_text": """
### Setup Instructions for Your Application

Your application is ready! Please fetch the changes and follow the steps below to configure it:

1. **Move the `.env.template` to `.env`**:
    Rename the `.env.template` file to `.env`:
    ```bash
    mv .env.template .env
    ```

2. **Update the `.env` file**:
    Open the `.env` file and replace the placeholder values with your actual environment variables and credentials. For example, replace `CHAT_ID_VAR` with `$chat_id` and fill in other necessary values.

    You might need to specify the path to .env file in your IDE run configurations.

3. **Start Your Application**:
    Once you've updated the `.env` file, you can start your application by running:
    ```bash
    python app.py
    ```
    or just run the app.py in your IDE.
Please also update your api.py files to use cyoda_token until authentication featute is fully implemented. Sorry for inconvenience!
Your application should now be up and running! 🎉

You can check the api with http://localhost:8000/docs

                       """,
                       "max_iteration": 0,
                       "stack": APP_BUILDING_STACK_KEY,
                       "publish": True},
                      {"question": None,
                       "prompt": {},
                       "answer": None,
                       "function": {"name": "finish_flow"},
                       "index": 2,
                       "iteration": 0,
                       "file_name": "entity/chat.json",
                       "notification_text": """
🎉 **Chat flow has been saved!** 🎉

The chat flow has been successfully saved to `entity/chat.json`. Now you can run `app.py` to start the application. 🚀

Once you run it, both the **workflow** and **entities** will be imported to the Cyoda environment automatically. 🌟

Any updates or changes to the entities will trigger the workflow, so you’re all set to go! 🔄

We are available in the **Google Tech Channel** to support you. If you spot any bugs or need additional features, feel free to submit tickets at [GitHub Issues](https://github.com/Cyoda-platform/ai-assistant). You’re also most welcome to contribute to the project! 💻 

For any direct inquiries, reach out to **ksenia.lukonina@cyoda.com**. We’re here to help! 😊
                       """,
                       "max_iteration": 0,
                       "stack": APP_BUILDING_STACK_KEY,
                       "publish": True},

                      # =======================================================
                      {"question": None,
                       "function": {"name": "register_workflow_with_app",
                                    "model_api": {"model": OPEN_AI_o3, "temperature": 0.7, "max_tokens": 10000},
                                    "prompt": {
                                        "text": """
Which workflow would you recommend for this code?  
Could you split this code into functions, each function should have name starting with 'process_'. These functions are async (example: async process_{{entity_name}}(entity: dict): )
It can take only one argument entity data and can modify this entity data state, so please also remove any unnecessary entity_service.update(this entity) calls = as you can do it by changing entity attributes directly, e.g. entity['attribute'] = new_value.
No more additional arguments can be passed.
Also, all workflow orchestration should be inside {workflow_function}. {workflow_function} should have only workflow orchestration code and no business logic. no other function can have workflow orchestration code.

{code}

You cannot apply entity_service.add/update/delete on the current entity (passed as argument)! if you need to change this entity state - modify directly  e.g. entity['attribute'].  The new state will be persisted. Do not any test/extra code.                      
Please return only compiled python code without additional information. If you'd like to add any comments please use # comment   
""",
                                        "api": {"model": OPEN_AI_o3, "temperature": 0.7, "max_tokens": 10000},
                                    },
                                    "workflow_prompt": """Please construct workflow json from this code using a typical finite-state machine (FSM) model.
The FSM consists of states and transitions between them, which can be represented as a directed graph where states are nodes, and transitions are edges.
Each transition may have processes. You need to add them if the user explicitly specifies them. Currently there can be only one transition coming from a single state.
Each state, except for the initial state (None), should be reachable from exactly one transition, ensuring that there are no isolated (disconnected) states in the workflow. Additionally, each transition must have both a start state and an end state.

Begin with an initial state labeled "None", which serves as the origin point.
Define transitions between states, with each state being an endpoint (i.e., target) of exactly one transition.
Ensure that all states (except "None") serve as the destination for exactly one transition to guarantee the graph remains fully connected.

JSON Example of the Workflow:
json
{{
  "name": "specify_name_that_describes_the_workflow",
  "description": "describe_the_workflow",
  "transitions": [
    {{
      "name": "spark_happy_message",
      "description": "Spark the happy message",
      "start_state": "None",
      "start_state_description": "Initial state",
      "end_state": "Happy_message_sparked",
      "end_state_description": "A happy message has been sparked",
      "automated": true
    }},
    {{
      "name": "send_happy_message",
      "description": "Send the happy message",
      "start_state": "Happy_message_sparked",
      "start_state_description": "A happy message has been sparked",
      "end_state": "Message_sent",
      "end_state_description": "The happy message has been sent",
      "automated": true #always put automated true
      "processes": {{
        "schedule_transition_processors": [],
        "externalized_processors": [
          {{
            "name": "process_example",
            "description": ""
          }}
        ]
      }}
    }}
  ]
}}
Please ensure that each process function is referenced in processes.externalized_processors 

{code}

Please return only valid json without any additional information.
"""
                                    },
                       "answer": None,
                       "index": 0,
                       "iteration": 0,
                       "flow_step": LOGIC_CODE_DESIGN_STR,
                       "max_iteration": 0,
                       "stack": API_REQUEST_STACK_KEY,
                       "publish": False},
                      {
                          "question": None,
                          "prompt": {},
                          "answer": None,
                          "function": {"name": "refresh_context",
                                       "model_api": {"model": OPEN_AI, "temperature": 0.7}},
                          "iteration": 0,
                          "flow_step": ENTITIES_DESIGN_STR,
                          "max_iteration": 0,
                          "stack": APP_BUILDING_STACK_KEY},

                      {"question": None,
                       "prompt": {
                           "text": """
Please return complete refactored application with all functions implemented.
No detail can be missed. Reason about potential issues and prevent them.
Please return only compiled python code without additional information. If you'd like to add any comments please use # comment
                           """,
                           "api": {"model": OPEN_AI_o3, "temperature": 0.7, "max_tokens": 10000},
                       },
                       "file_name": "entity/prototype_cyoda_workflow.py",
                       "answer": None,
                       "function": None,
                       "iteration": 0,
                       "flow_step": GATHERING_REQUIREMENTS_STR,
                       "max_iteration": 0,
                       "stack": APP_BUILDING_STACK_KEY,
                       "publish": False},
                      {"question": None,
                       "prompt": {
                           "text": """
What do you think, can we move any logic from the endpoint inside newly added functions (workflow=process_{entity_name}) that will be invoked right before persisting entity.
It will make our code more robust and will 'free' the controllers from excessive logic.
Any async task (including fire and forget functions) is definitely a candidate to be replaced with process_{entity_name} function as workflow function supports asynchronous code and is a direct alternative for such tasks. It is the right approach - this is required.
Workflow function applied to the entity asynchronously before persistence. this function takes this entity data as the only argument. You can change entity state inside this function e.g. entity['attribute'] = new_value
You can get and add secondary/supplementary/raw data entities of a different entity_model
You cannot apply entity_service.add/update/delete on the current entity! if you need to change this entity state - modify directly  e.g. entity['attribute'].  The new state will be persisted.                        
                           """,
                           "api": {"model": OPEN_AI_o3, "temperature": 0.7, "max_tokens": 10000},
                       },
                       "file_name": "entity/prototype_cyoda_workflow.py",
                       "answer": None,
                       "function": None,
                       "iteration": 0,
                       "flow_step": GATHERING_REQUIREMENTS_STR,
                       "max_iteration": 0,
                       "stack": APP_BUILDING_STACK_KEY,
                       "publish": False},
                      {"question": None,
                       "prompt": {
                           "text": """
Hello, entity_service.add_item has changed, now it additionally expects entity workflow function as an argument. this function will be applied to the entity before it is persisted
e.g.
entity_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="{entity_name}",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=data,  # the validated data object
        workflow=process_{entity_name} # Workflow function applied to the entity asynchronously before persistence. this function takes this entity data as the only argument. You can change entity state inside this function, get and add entities with a different entity_model (but cannot add/update/delete entity of the same entity_model - it will cause infinite recursion) 
    )
could you please update this code: add workflow function as a parameter and implement it. Return complete code.
Please return only compiled python code without additional information. If you'd like to add any comments please use # comment
                           """,
                           "api": {"model": OPEN_AI_o3, "temperature": 0.7, "max_tokens": 10000},
                           "attached_files": ["entity/prototype_cyoda.py"]
                       },
                       "file_name": "entity/prototype_cyoda_workflow.py",
                       "answer": None,
                       "function": None,
                       "iteration": 0,
                       "flow_step": GATHERING_REQUIREMENTS_STR,
                       "max_iteration": 0,
                       "stack": APP_BUILDING_STACK_KEY,
                       "publish": False},
                      # ==================================================================================
                      {
                          "question": None,
                          "prompt": {},
                          "answer": None,
                          "function": {"name": "refresh_context",
                                       "model_api": {"model": OPEN_AI, "temperature": 0.7}},
                          "iteration": 0,
                          "flow_step": ENTITIES_DESIGN_STR,
                          "max_iteration": 0,
                          "stack": APP_BUILDING_STACK_KEY},
                      # =========================================================================================
                      {"question": None,
                       "function": {
                           "name": "generate_entities_template",
                           "model_api": {"model": OPEN_AI, "temperature": 0.7, "max_tokens": 10000},
                           "prompt": {
                               "text": "Please, transform data about entities {entities_list} into the following json: {{ \"entities\": [ {{ \"entity_name\": \"\", //put entity name here, lowercase, underscore \\n \"entity_data_example\": \"\", //put entity data golden json example according to the requirement, list all entity attributes specified by the user or relevant to the request body}} ] }}",
                               "api": {"model": OPEN_AI, "temperature": 0.7},
                               "attached_files": ["entity/prototype_cyoda.py", "entity/functional_requirement.md"],
                               "schema": {
                                   "$schema": "http://json-schema.org/draft-07/schema#",
                                   "title": "Generated schema for Root",
                                   "type": "object",
                                   "properties": {
                                       "entities": {
                                           "type": "array",
                                           "items": {
                                               "type": "object",
                                               "properties": {
                                                   "entity_name": {
                                                       "type": "string"
                                                   },
                                                   "entity_data_example": {
                                                       "type": "object",
                                                       "properties": {}
                                                   }
                                               },
                                               "required": [
                                                   "entity_name",
                                                   "entity_data_example"
                                               ]
                                           }
                                       }
                                   },
                                   "required": [
                                       "entities"
                                   ]
                               }},
                       },
                       "file_name": "entity/entities_data_design.json",
                       "answer": None,
                       "iteration": 0,
                       "flow_step": GATHERING_REQUIREMENTS_STR,
                       "max_iteration": 0,
                       "stack": APP_BUILDING_STACK_KEY,
                       "publish": False},
                      {
                          "question": None,
                          "prompt": {},
                          "answer": None,
                          "function": {"name": "refresh_context",
                                       "model_api": {"model": OPEN_AI, "temperature": 0.7}},
                          "iteration": 0,
                          "flow_step": ENTITIES_DESIGN_STR,
                          "max_iteration": 0,
                          "stack": APP_BUILDING_STACK_KEY},
                      # ================================================
#                       {"question": None,
#                        "prompt": {
#                            "text": "Please return fully functioning prototype_cyoda.py code taking into account user suggestions if any. Please return only compiled python code without additional information. If you'd like to add any comments please use # comment",
#                            "api": {"model": OPEN_AI_o3, "temperature": 0.7, "max_tokens": 10000},
#                            "attached_files": ["entity/prototype_cyoda.py"]
#                        },
#                        "file_name": "entity/prototype_cyoda.py",
#                        "answer": None,
#                        "function": None,
#                        "iteration": 0,
#                        "flow_step": GATHERING_REQUIREMENTS_STR,
#                        "max_iteration": MAX_ITERATION,
#                        "additional_questions": [
#                            {"question": f"{APPROVAL_NOTIFICATION}", "approve": True}],
#                        "stack": APP_BUILDING_STACK_KEY,
#                        "publish": False},
#                       {
#                           "question": """Prototype with persistence to Cyoda Entity Database is  Ready for Validation
#
# We have completed the first prototype for your functional requirements.
#
# To validate the API, please follow the steps below:
#
# **1. Run the Application**
#
# Execute the following command to start the application:
#
# ```python
# python entity/prototype_cyoda.py
# ```
#
# 2. Validate the API
# Once the application is running, open your browser and navigate to:
# ```
# http://localhost:8000/docs
# ```
# Request and response examples are available in entity/functional_requirement.md
#
# This will allow you to validate the API response.
# """,
#                           "prompt": None,
#                           "answer": None,
#                           "function": None,
#                           "iteration": 0,
#                           "flow_step": GATHERING_REQUIREMENTS_STR,
#                           "max_iteration": 0,
#                           "approve": True,
#                           "stack": APP_BUILDING_STACK_KEY,
#                           "publish": False},

                      # {"question": None,
                      #  "prompt": {
                      #      "text": "Hello! Please provide mermaid entity ER diagrams and class diagrams for each entity (identify in prototype_cyoda.py by entity_model added in entity service). Base your answer on the provided documents. You cannot deviate from them.",
                      #      "api": {"model": OPEN_AI, "temperature": 0.2},
                      #      # todo - add pattern/**
                      #      "attached_files": ["entity/prototype_cyoda.py", "entity/functional_requirement.md"]
                      #  },
                      #  "file_name": "entity/entities_data_design.md",
                      #  "answer": None,
                      #  "function": None,
                      #  "iteration": 0,
                      #  "flow_step": GATHERING_REQUIREMENTS_STR,
                      #  "max_iteration": 0,
                      #  "stack": APP_BUILDING_STACK_KEY,
                      #  "publish": True},
                      {"question": None,
                       "prompt": {
                           "text": """

You are provided with a Python codebase that implements a REST API (using a framework like Quart, Flask, etc.). Currently, the code uses local in‑memory dictionaries (and counters) to store and manage data for one or more entity types. Your task is to refactor the code so that all interactions with the local cache are replaced by calls to an external service called entity_service (from app_init.app_init import entity_service).
You can use only these functions for replacement - if this is not enough just skip and leave as is
1.
id = await entity_service.add_item(
    token=cyoda_token,
    entity_model="{entity_name}",
    entity_version=ENTITY_VERSION,  # always use this constant
    entity=data  # the validated data object
)
just return id in the response - you cannot immediately retrieve the result - it should be retrieved via separate endpoint
2. Data retrieval: 
await entity_service.get_item(
    token=cyoda_token,
    entity_model="{entity_name}",
    entity_version=ENTITY_VERSION,
    technical_id=<id>
)
await entity_service.get_items(
    token=cyoda_token,
    entity_model="{entity_name}",
    entity_version=ENTITY_VERSION,
)
await entity_service.get_items_by_condition(
    token=cyoda_token,
    entity_model="{entity_name}",
    entity_version=ENTITY_VERSION,
    condition=condition
)
3. 
await entity_service.update_item(
    token=cyoda_token,
    entity_model="{entity_name}",
    entity_version=ENTITY_VERSION,  # always use this constant
    entity=data,
    technical_id=id,
    meta={}
)
4.
await entity_service.delete_item(
    token=cyoda_token,
    entity_model="{entity_name}",
    entity_version=ENTITY_VERSION,  # always use this constant
    technical_id=id,
    meta={}
)
use 'from common.config.config import ENTITY_VERSION' to import ENTITY_VERSION
Add this code:
```
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
```
Preserve the endpoint routes and any other essential business logic.
Please make sure you keep all the necessary business logic, like data ingestion, calling any external apis , mocks, calculations etc
Please return only compiled python code without additional information. If you'd like to add any comments please use # comment

                           """,
                           "api": {"model": OPEN_AI_o3, "temperature": 0.7, "max_tokens": 10000},
                           "attached_files": ["entity/prototype.py"]
                       },
                       "file_name": "entity/prototype_cyoda.py",
                       "answer": None,
                       "function": None,
                       "iteration": 0,
                       "flow_step": GATHERING_REQUIREMENTS_STR,
                       "max_iteration": 0,
                       "stack": APP_BUILDING_STACK_KEY,
                       "publish": False},

                      # ================================================
                      {
                          "question": None,
                          "prompt": {},
                          "answer": None,
                          "function": {"name": "refresh_context",
                                       "model_api": {"model": OPEN_AI, "temperature": 0.7}},
                          "iteration": 0,
                          "flow_step": ENTITIES_DESIGN_STR,
                          "max_iteration": 0,
                          "stack": APP_BUILDING_STACK_KEY},
                      {
                          "notification": """
Awesome! Let's dive into generating your application code! 🚀 

I'll keep you updated with notifications on my progress, and let you know when it's time to discuss any changes.
 
Feel free to grab a coffee ☕ while I work—it's going to take about 2 minutes. 
 
Just relax and wait for the update!

In this process, we will walk through each stage of building an application, from gathering initial requirements to designing, coding, and implementing the final logic.

### The stages of the process are as follows:

1. **Entities design**:  
   Let's define the JSON data structure for each entity.
   *Output documents*: entity/*

2. **Workflow design**:  
   Let's ensure our entity workflow is correctly defined.
   *Output documents*: entity/*/workflow.json

3. **Workflow processors code design**:  
   Let's implement the workflow processors.
   *Output documents*: entity/*/workflow.py                         
""",
                          "prompt": None,
                          # "file_name": "entity/app_design.json",
                          "answer": None,
                          "function": None,
                          "iteration": 0,
                          "flow_step": GATHERING_REQUIREMENTS_STR,
                          "max_iteration": MAX_ITERATION,
                          "stack": APP_BUILDING_STACK_KEY,
                          "approve": True,
                          "publish": True},
                      {"question": None,
                       "prompt": {
                           "text": EMPTY_PROMPT,
                           "api": {"model": OPEN_AI, "temperature": 0.7},
                       },
                       "answer": None,
                       "approve": False,
                       "function": None,
                       "iteration": 0,
                       "flow_step": GATHERING_REQUIREMENTS_STR,
                       "max_iteration": MAX_ITERATION * 10,
                       "additional_questions": [
                           {
                               "question": "Feel free to ask any questions or discuss the design in the chat 💬💬",
                               "approve": True}],
                       "stack": APP_BUILDING_STACK_KEY,
                       "publish": True},
                      {
                          "question": """
                          
Congratulations on successfully completing your application prototype!🥳
 
You’ve put in a lot of hard work to bring your idea to life, and it’s truly exciting to see it in action. 

🪅🪅🪅This is an important milestone—well done!🪅🪅🪅

However, as impressive as your prototype is, it’s not yet fully robust. A few critical components are missing:

**Scalability and High Availability**

**Persistence and Data Integrity**

**Production-Ready Features**

To address these gaps and ensure your application can handle real-world demands, we recommend refactoring your solution using the Cyoda Framework. By deploying to a High Availability (HA) cluster on Cyoda Cloud, you’ll benefit from:

**Enterprise-grade reliability and failover capabilities**

**Seamless data persistence**

**Streamlined deployment and scaling processes**

**A comprehensive set of production-ready tools and services**

We believe this transformation will empower your application to reach its full potential. Would you like to proceed with refactoring your prototype to make it robust, production-ready, and fully deployable on Cyoda Cloud?

Just give me a thumbs up! 👍 
                          """,
                          "prompt": None,
                          # "file_name": "entity/app_design.json",
                          "answer": None,
                          "function": None,
                          "iteration": 0,
                          "flow_step": GATHERING_REQUIREMENTS_STR,
                          "max_iteration": MAX_ITERATION,
                          "stack": APP_BUILDING_STACK_KEY,
                          "approve": True,
                          "publish": True},
                      {"question": None,
                       "prompt": {
                           "text": "Please return fully functioning prototype.py code taking into account user suggestions if any. You cannot use sqlalchemy in the prototype or any external implementation for persistence or cache, only local cache. if the user made any changes they take precedence.",
                           "api": {"model": OPEN_AI_o3, "temperature": 0.7, "max_tokens": 10000},
                           "attached_files": ["entity/prototype.py"]
                       },
                       "file_name": "entity/prototype.py",
                       "answer": None,
                       "function": None,
                       "iteration": 0,
                       "flow_step": GATHERING_REQUIREMENTS_STR,
                       "max_iteration": MAX_ITERATION,
                       "additional_questions": [
                           {"question": f"{APPROVAL_NOTIFICATION}", "approve": True}],
                       "stack": APP_BUILDING_STACK_KEY,
                       "publish": True},
                      {
                          "question": """First Prototype Ready for Validation

We have completed the first prototype for your functional requirements. 

To validate the API, please follow the steps below:

**1. Run the Application**

Execute the following command to start the application:

```python 
python entity/prototype.py
```

2. Validate the API
Once the application is running, open your browser and navigate to:
```
http://localhost:8000/docs
```
Request and response examples are available in entity/functional_requirement.md

This will allow you to validate the API response.
""",
                          "prompt": None,
                          "answer": None,
                          "function": None,
                          "iteration": 0,
                          "flow_step": GATHERING_REQUIREMENTS_STR,
                          "max_iteration": 0,
                          "approve": True,
                          "stack": APP_BUILDING_STACK_KEY,
                          "publish": True},
                      # =============================================

                      {"question": None,
                       "prompt": {
                           "text": """ Please, add @validate_request to each request based on quart-schema lib example: 
from dataclasses import dataclass
from quart_schema import QuartSchema, validate_request, validate_response

app = Quart(__name__)
QuartSchema(app)

@dataclass
class Todo:
    task: str #please use only primitives

post/put request: 
@app.route("/test", methods=["POST"]) - this line should go first in post method
@validate_request(Todo)
async def create_todo(data: Todo)

get request with request parameters:
@validate_querystring(Todo) - this line should go first in get method
@app.route("/test", methods=["GET"])
async def get_todo() #cannot put body to GET request! - please make sure you do not pass any arguments! it will throw ar error. only post and put can have body

get request without request parameters *no validation needed*:
@app.route("/companies/<string:id>/lei", methods=["GET"])

Correct example:
@validate_querystring(Todo) - this line should go first in get
@app.route("/test", methods=["GET"])
async def todo():
 name = request.args.get('name') #use standard approach to access parameters values for GET requests, you cannot access Todo in GET

Wrong example:
@app.route("/test", methods=["GET"])
@validate_querystring(Todo)- this line should go first in get
async def todo(query_args: Todo): - do not do like this please

Correct example:
@app.route("/test", methods=["POST"]) - this line should go first in post method
@validate_request(Todo) - this line should go second in post method, but first in get
async def create_todo(data: Todo)


Wrong example:
@validate_request(Todo) - this line should go second in post method, but first in get
@app.route("/test", methods=["POST"]) - this line should go first in post method
async def create_todo(data: Todo)

I know this iss confusing - i think there is an issue in quart schema library so we have to workaround this issue:
Always put validation first for GET requests, and last for POST requests. Reason about this issue and make correct decision.
Also put a comment that it is an issue workaround, so that everyone knows the logic behind.
Please return only compiled python code without additional information. If you'd like to add any comments please use # comment

""",
                           "api": {"model": OPEN_AI_o3, "temperature": 0.7, "max_tokens": 10000},
                           "attached_files": ["entity/prototype.py"]
                       },
                       "answer": None,
                       "function": None,
                       "iteration": 0,
                       "flow_step": GATHERING_REQUIREMENTS_STR,
                       "max_iteration": 0,
                       "stack": APP_BUILDING_STACK_KEY,
                       "file_name": "entity/prototype.py",
                       "publish": True},

                      {"question": None,
                       "prompt": {
                           "text": """
Now that we’ve finalized the API design, please provide the code for the prototype.py file.
The implementation should be a working prototype rather than a fully robust solution. 
Incorporate any details I’ve already specified—such as external APIs, models, or specific calculations—and use mocks or placeholders only where requirements are unclear or incomplete. 
Wherever you introduce a mock or placeholder, include a TODO comment to indicate the missing or uncertain parts. 
The goal is to verify the user experience (UX) and identify any gaps in the requirements before we proceed with a more thorough implementation.
Please double-check you are using all the information provided earlier. Use aiohttp.ClientSession for http requests, and Quart api. 
Use QuartSchema(app) but do not add any @validate_request as our data is dynamic, just add QuartSchema(app) one line.
Use this entry point: if __name__ == '__main__':app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True).
Mock any persistence, do not use any particular implementation, just local cache (e.g. you cannot use sqlalchemy in the prototype or any external implementation for persistence or cache).
You are most welcome to use such pattern where it is reasonable:
entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}
# Fire and forget the processing task.
await asyncio.create_task(process_entity(entity_job, data.__dict__))

""",

                           "api": {"model": OPEN_AI_o3, "temperature": 0.7, "max_tokens": 10000},
                       },
                       "answer": None,
                       "function": None,
                       "iteration": 0,
                       "flow_step": GATHERING_REQUIREMENTS_STR,
                       "max_iteration": 0,
                       "stack": APP_BUILDING_STACK_KEY,
                       "file_name": "entity/prototype.py",
                       "publish": False},
                      {
                          "notification": "Let's proceed to generating the fist prototype. Please, give me a moment to think everything over",
                          "prompt": None,
                          # "file_name": "entity/app_design.json",
                          "answer": None,
                          "function": None,
                          "iteration": 0,
                          "flow_step": GATHERING_REQUIREMENTS_STR,
                          "max_iteration": MAX_ITERATION,
                          "stack": APP_BUILDING_STACK_KEY,
                          "approve": True,
                          "publish": True},
                      {"question": None,
                       "prompt": {
                           "text": """Please return well-formatted final functional requirements.""",
                           "api": {"model": OPEN_AI, "temperature": 0.7}
                       },
                       # "file_name": "entity/app_design.json",
                       "answer": None,
                       "function": None,
                       "iteration": 0,
                       "flow_step": GATHERING_REQUIREMENTS_STR,
                       "max_iteration": 0,
                       "stack": APP_BUILDING_STACK_KEY,
                       "file_name": "entity/functional_requirement.md",
                       "publish": False},
                      {"question": None,
                       "prompt": {
                           "text": "Please answer the question and return the full functional requirement. User says: ",
                           "api": {"model": OPEN_AI, "temperature": 0.7}
                       },
                       "file_name": "entity/functional_requirement.txt",
                       "answer": None,
                       "function": None,
                       "iteration": 0,
                       "flow_step": GATHERING_REQUIREMENTS_STR,
                       "max_iteration": MAX_ITERATION,
                       "additional_questions": [
                           {"question": f"{APPROVAL_NOTIFICATION}", "approve": True}],
                       "stack": APP_BUILDING_STACK_KEY,
                       "publish": True},
                      {
                          "question": """Let's discuss the API for your application together. What would you recommend?
""",
                          "prompt": None,
                          "answer": None,
                          "function": None,
                          "iteration": 0,
                          "flow_step": GATHERING_REQUIREMENTS_STR,
                          "max_iteration": 0,
                          "approve": True,
                          "stack": APP_BUILDING_STACK_KEY,
                          "publish": True},
                      {"question": None,
                       "prompt": {
                           "text": """Please, help me define the functional requirements for my project.
Outline the necessary API endpoints (adhering to Restful rules, any business logic that invokes external data source, retrieves data or does any calculations needs to be done in POST endpoint, GET is used only for my application results retrieval (external data retrieval should be implemented in POST endpoint)),
including details on request/response formats. Additionally, provide a visual representation of the user-app interaction using Mermaid diagrams (e.g. journey/sequence).
Please return markdown document without any additional information. 
Each diagram should be wrapped into ```mermaid ...```
""",
                           "api": {"model": OPEN_AI_o3, "temperature": 0.7}
                       },
                       # "file_name": "entity/app_design.json",
                       "answer": None,
                       "function": None,
                       "iteration": 0,
                       "flow_step": GATHERING_REQUIREMENTS_STR,
                       "max_iteration": 0,
                       "stack": APP_BUILDING_STACK_KEY,
                       # "file_name": "entity/functional_requirement.md",
                       "publish": True},
                      {"question": None,
                       "prompt": {
                           "text": EMPTY_PROMPT,
                           "api": {"model": OPEN_AI, "temperature": 0.7}
                       },
                       # "file_name": "entity/app_design.json",
                       "answer": None,
                       "function": None,
                       "iteration": 0,
                       "flow_step": GATHERING_REQUIREMENTS_STR,
                       "max_iteration": MAX_ITERATION,
                       "additional_questions": [
                           {"question": f"{APPROVAL_NOTIFICATION}", "approve": True}],
                       "stack": APP_BUILDING_STACK_KEY,
                       "publish": True},
                      {"question": None,
                       "prompt": {
                           "text": """Hello! You are a python quart developer.
You're building a backend application. Currently you are focusing on functional requirements, 
and will cover any non-functional requirement later. 
Let's analyse this request for application building, and clarify any important functional requirements 
that necessary.
Ask questions if something is not clear enough and make suggestions that will help us formulate formal specification in the next iterations. 
Make sure your answers are friendly but up-to-the point and do not start with any exclamations, but rather answer the question. 
Max tokens = 300. Here is my requirement: """,
                           "api": {"model": OPEN_AI, "temperature": 0.7, "max_tokens": 10000}
                       },
                       # "file_name": "entity/app_design.json",
                       "answer": None,
                       "function": None,
                       "iteration": 0,
                       "flow_step": GATHERING_REQUIREMENTS_STR,
                       "max_iteration": 0,
                       "stack": APP_BUILDING_STACK_KEY,
                       "publish": True},

                      {
                          "question": "💡 What kind of application would you like to build? I'd love to hear your ideas! Feel free to share them with me! 😊",
                          "prompt": {},
                          "answer": None,
                          "function": None,
                          "iteration": 0,
                          "file_name": "entity/app_design.json",
                          "flow_step": GATHERING_REQUIREMENTS_STR,
                          "approve": False,
                          "example_answers": [
                              """
                              Hello, I would like to download the following data: [London Houses Data](https://raw.githubusercontent.com/Cyoda-platform/cyoda-ai/refs/heads/ai-2.x/data/test-inputs/v1/connections/london_houses.csv), analyze it using **pandas**, and save a report. 📊""",
                              """
                              Hello! 👋
                              I would like to develop an application that:
                              1. Ingests data from a specified data source 📥
                              2. Aggregates the data 🧮
                              3. Saves the aggregated data to a report 📄
                              Once the report is generated, the application should send it to the admin's email 📧. 
                              Additionally, the data ingestion process should be scheduled to run **once a day** ⏰."""],
                          "max_iteration": 0,
                          "stack": APP_BUILDING_STACK_KEY,
                          "publish": True},
                      {"question": None,
                       "prompt": {},
                       "answer": None,
                       "function": {"name": "init_chats"},
                       "flow_step": GATHERING_REQUIREMENTS_STR,
                       "iteration": 0,
                       "max_iteration": 0,
                       "stack": APP_BUILDING_STACK_KEY,
                       },
                      {"question": None,
                       "prompt": {},
                       "answer": None,
                       "function": {"name": "clone_repo"},
                       "iteration": 0,
                       "flow_step": GATHERING_REQUIREMENTS_STR,
                       "max_iteration": 0,
                       "stack": APP_BUILDING_STACK_KEY,
                       "publish": True
                       },
                      {
                          "notification": """
👋 Welcome to Cyoda Application Builder! We’re excited to build something amazing with you! 😄  

We’re here to help with building and deploying on Cyoda Cloud! Reach out anytime! 🌟 Your branch will be ready soon, and I’ll notify you when I push changes. If you have suggestions, message me or use Canvas! 😊  

In Canvas, you can code, edit, and improve around the main app build flow! It’s a great way to collaborate and make changes! 💻  

If you’re happy with the progress or want me to pull your changes, just give me a thumbs up! 👍  (currently approve button in the top panel)

If something goes wrong, no worries—just roll back! 😬 Your app will be live on Cyoda Platform GitHub soon! 🚀 Let’s build your branch together! 🌿
""",
                          "prompt": {},
                          "answer": None,
                          "function": None,
                          "iteration": 0,
                          "info": True,
                          "file_name": "instruction.txt",
                          "max_iteration": 0,
                          "stack": APP_BUILDING_STACK_KEY,
                          "publish": True

                      }
                      ]
