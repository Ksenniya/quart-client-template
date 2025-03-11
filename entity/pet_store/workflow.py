import httpx

async def process_fetch_petstore_data(entity: dict):
    # Define the URL for the pet store API
    petstore_api_url = "https://api.example.com/petstore"  # Replace with the actual API URL

    # Fetch data from the pet store API
    async with httpx.AsyncClient() as client:
        response = await client.get(petstore_api_url)

        # Check if the request was successful
        if response.status_code == 200:
            # Assuming the returned JSON is structured similarly to the entity example
            petstore_data = response.json()
            
            # Update the entity with the fetched data
            entity["petstore_data"] = petstore_data
            entity["workflowProcessed"] = True
        else:
            entity["error"] = f"Failed to fetch data: {response.status_code}"
            entity["workflowProcessed"] = False