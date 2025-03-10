from quart import Quart, jsonify, request
import httpx

app = Quart(__name__)

BASE_URL = 'https://petstore.swagger.io/v2'

@app.route('/pets', methods=['GET'])
async def get_pets():
    response = await httpx.get(f'{BASE_URL}/pet/findByStatus', params={'status': 'available'})
    return jsonify(response.json())

@app.route('/pet', methods=['POST'])
async def add_pet():
    pet_data = request.json
    response = await httpx.post(f'{BASE_URL}/pet', json=pet_data)
    return jsonify(response.json()), response.status_code

@app.route('/order', methods=['POST'])
async def place_order():
    order_data = request.json
    response = await httpx.post(f'{BASE_URL}/store/order', json=order_data)
    return jsonify(response.json()), response.status_code

if __name__ == '__main__':
    app.run(debug=True)