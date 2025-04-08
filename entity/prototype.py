```python
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass
import httpx
import asyncio
import logging
from datetime import datetime

app = Quart(__name__)
QuartSchema(app)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# In-memory user and calculation results storage
users = {}
calculations = {}

@dataclass
class UserRegistration:
    username: str
    email: str
    password: str

@dataclass
class UserLogin:
    email: str
    password: str

@dataclass
class CalculationRequest:
    inputData: str

@app.route('/api/users/register', methods=['POST'])
@validate_request(UserRegistration)  # Validation last for POST requests
async def register_user(data: UserRegistration):
    user_id = str(len(users) + 1)  # Simple user ID generation
    users[user_id] = {
        "username": data.username,
        "email": data.email,
        "password": data.password  # TODO: Hash passwords in production
    }
    return jsonify({"message": "User registered successfully", "userId": user_id}), 201

@app.route('/api/users/login', methods=['POST'])
@validate_request(UserLogin)  # Validation last for POST requests
async def login_user(data: UserLogin):
    for user_id, user in users.items():
        if user["email"] == data.email and user["password"] == data.password:
            return jsonify({"message": "Login successful", "token": "fake_token"}), 200  # TODO: Implement JWT
    return jsonify({"message": "Invalid credentials"}), 401

@app.route('/api/users/profile', methods=['GET'])
async def get_user_profile():
    # TODO: Authenticate user and retrieve user ID from token
    user_id = "1"  # Placeholder
    user = users.get(user_id)
    if user:
        return jsonify({"userId": user_id, "username": user["username"], "email": user["email"]}), 200
    return jsonify({"message": "User not found"}), 404

@app.route('/api/data/calculate', methods=['POST'])
@validate_request(CalculationRequest)  # Validation last for POST requests
async def calculate_data(data: CalculationRequest):
    job_id = str(len(calculations) + 1)
    requested_at = datetime.utcnow()
    calculations[job_id] = {"status": "processing", "requestedAt": requested_at}
    
    # Fire-and-forget processing task
    await asyncio.create_task(process_entity(job_id, data.inputData))
    return jsonify({"message": "Calculation initiated", "jobId": job_id}), 202

async def process_entity(job_id, input_data):
    try:
        # TODO: Replace with actual external API call
        async with httpx.AsyncClient() as client:
            response = await client.post("https://api.example.com/calculate", json={"data": input_data})
            result = response.json()  # Assume this returns the calculation result
            calculations[job_id]["result"] = result  # Store the result
            calculations[job_id]["status"] = "completed"
    except Exception as e:
        logger.exception(e)
        calculations[job_id]["status"] = "failed"

@app.route('/api/data/results', methods=['GET'])
async def get_results():
    return jsonify({"results": calculations}), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```