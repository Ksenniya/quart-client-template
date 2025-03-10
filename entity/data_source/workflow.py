def process_fetch_post_data(entity):
    """
    Process to fetch post data from the provided API.
    
    Args:
        entity (str): The URL of the API to fetch data from.
    
    Returns:
        dict: The fetched post data as a dictionary.
    """
    import requests
    
    response = requests.get(entity)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to fetch data: {response.status_code}")


def process_process_fetched_data(entity):
    """
    Process the fetched post data for further use.
    
    Args:
        entity (dict): The fetched post data as a dictionary.
    
    Returns:
        str: A summary of the processed data.
    """
    # Example processing logic
    title = entity.get('title', 'No Title')
    body = entity.get('body', 'No Body')
    summary = f"Title: {title}\nBody: {body}"
    
    # Here you could add more complex processing as needed
    return summary