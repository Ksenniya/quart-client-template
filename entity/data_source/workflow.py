import requests

async def process_fetch_data(entity: dict):
    try:
        response = requests.get("https://jsonplaceholder.typicode.com/posts/1")
        data = response.json()
        entity["fetched_data"] = data
        entity["workflowProcessed"] = True
    except Exception as e:
        entity["error"] = str(e)
        entity["workflowProcessed"] = False

async def process_process_data(entity: dict):
    if "fetched_data" in entity:
        # Example processing: Extract the title and body from the fetched data
        title = entity["fetched_data"].get("title", "")
        body = entity["fetched_data"].get("body", "")
        entity["processed_data"] = {
            "title": title,
            "body": body
        }
        entity["workflowProcessed"] = True
    else:
        entity["error"] = "No data fetched for processing."
        entity["workflowProcessed"] = False