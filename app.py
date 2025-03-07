import httpx

@app.route('/store/inventory', methods=['GET'])
async def get_inventory():
    async with httpx.AsyncClient() as client:
        response = await client.get('https://petstore.swagger.io/v2/store/inventory')
        return response.json(), response.status_code

#put_application_code_here
