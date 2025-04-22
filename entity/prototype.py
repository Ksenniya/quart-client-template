```python
from dataclasses import dataclass
from quart import Quart, request
from quart_schema import QuartSchema, validate_request, validate_querystring

app = Quart(__name__)
QuartSchema(app)

@dataclass
class Login:
    username: str
    password: str

@dataclass
class Register:
    username: str
    password: str
    email: str

@dataclass
class DataRetrieve:
    query: str

@dataclass
class UserProfile:
    id: int

# POST /api/auth/login
@app.route("/api/auth/login", methods=["POST"])  # This line should go first in POST method
@validate_request(Login)  # Validation for POST should be last
async def login(data: Login):
    # Logic for user login
    pass

# POST /api/auth/register
@app.route("/api/auth/register", methods=["POST"])  # This line should go first in POST method
@validate_request(Register)  # Validation for POST should be last
async def register(data: Register):
    # Logic for user registration
    pass

# POST /api/data/retrieve
@app.route("/api/data/retrieve", methods=["POST"])  # This line should go first in POST method
@validate_request(DataRetrieve)  # Validation for POST should be last
async def retrieve_data(data: DataRetrieve):
    # Logic for data retrieval
    pass

# GET /api/data/results
@app.route("/api/data/results", methods=["GET"])  # This line should go first in GET method
@validate_querystring(DataRetrieve)  # Validation for GET should be first (workaround for issue)
async def get_results():
    # Logic for retrieving results
    pass

# GET /api/users/<id>
@app.route("/api/users/<int:id>", methods=["GET"])  # This line should go first in GET method
async def get_user_profile(id: int):  # No validation needed for GET request
    # Logic for fetching user profile
    pass
```