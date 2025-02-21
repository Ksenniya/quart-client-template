Below is one possible refactored version of the prototype that replaces the local in‑memory caches with calls to the external entity_service. (Note that if any particular external call does not support an operation “out‐of‐the‐box” then we simply “skip and leave as is” the non‑migrated logic.) You’ll need to verify (or adapt) the entity names (“transactions” and “orders”) with what your service expects.

File: entity/prototype.py

------------------------------------------------
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from dataclasses import dataclass, field
from typing import List, Optional
import aiohttp

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response  # for GET endpoints you don’t need query validations

# Import external entity service functions and constants
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # one‑line initialization as required

# Remove the in‑memory cache dictionaries – all data is now stored externally.
# transactions_db = {}  # no longer used
# orders_db = {}        # no longer used

# Add startup routine to initialize cyoda connection
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Data Models for Requests and Responses

@dataclass
class TransactionItem:
    # All fields use primitives. Optional fields use default values
    transactionId: Optional[str] = None
    amount: float = 0.0
    type: str = ""
    timestamp: Optional[str] = None

@dataclass
class TransactionsWrapper:
    transactions: List[TransactionItem] = field(default_factory=list)

@dataclass
class ProcessedResult:
    transactionId: str
    orderId: str
    reviewStatus: str

@dataclass
class CreateTransactionsResponse:
    status: str
    processed: List[ProcessedResult] = field(default_factory=list)

# Helper function to simulate external review logic.
# After obtaining the review outcome we update the order using entity_service.update_item.
async def process_entity(order_id: str, transaction_id: str):
    async with aiohttp.ClientSession() as session:
        try:
            # TODO: Replace URL and payload with actual external API details.
            external_url = "http://external-review-api/validate"  # Placeholder URL
            payload = {"transactionId": transaction_id}
            async with session.post(external_url, json=payload) as resp:
                if resp.status == 200:
                    review_data = await resp.json()
                    outcome = review_data.get("reviewStatus", "approved")
                else:
                    outcome = "failed review"
        except Exception as e:
            # In production, replace print with proper logging.
            print(f"Error calling external API for order {order_id}: {e}")
            outcome = "failed review"
    # Mimic processing delay
    await asyncio.sleep(0.1)
    # Retrieve the order from the external service, update review information, and persist the change.
    order_obj = entity_service.get_item(
        token=cyoda_token,
        entity_model="orders",
        entity_version=ENTITY_VERSION,
        technical_id=order_id
    )
    if order_obj:
        order_obj["reviewStatus"] = outcome
        order_obj["reviewTimestamp"] = datetime.datetime.utcnow().isoformat()
        entity_service.update_item(
            token=cyoda_token,
            entity_model="orders",
            entity_version=ENTITY_VERSION,
            entity=order_obj,
            meta={}
        )

# POST endpoint for creating transactions
@app.route('/transactions', methods=['POST'])
@validate_request(TransactionsWrapper)  # For POST endpoints: route -> validate_request -> validate_response.
@validate_response(CreateTransactionsResponse, 201)
async def create_transactions(data: TransactionsWrapper):
    processed_results = []
    # Iterate through all transactions provided in the request
    for tx in data.transactions:
        # Use provided ID or assign a new one if missing.
        internal_id = tx.transactionId or str(uuid.uuid4())
        tx.transactionId = internal_id
        # Use provided timestamp or assign current UTC time if missing.
        tx.timestamp = tx.timestamp or datetime.datetime.utcnow().isoformat()
        
        # Convert the transaction data (a dataclass instance) to dict.
        tx_dict = tx.__dict__
        # Call the external service to add the transaction.
        # The returned id will be added to the response so that the user can query by id.
        external_tx_id = entity_service.add_item(
            token=cyoda_token,
            entity_model="transactions",  # entity name for transactions
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=tx_dict  # the validated data object
        )
        
        # Create an order for this transaction with initial review status.
        order_id = str(uuid.uuid4())
        order_data = {
            "orderId": order_id,  # initial local id; note that the external service call will yield the official id.
            "transactionId": external_tx_id,
            "reviewStatus": "pending review",
            "requestedAt": datetime.datetime.utcnow().isoformat()
        }
        external_order_id = entity_service.add_item(
            token=cyoda_token,
            entity_model="orders",  # entity name for orders
            entity_version=ENTITY_VERSION,
            entity=order_data
        )

        # Build the response with external ids.
        processed_results.append(ProcessedResult(
            transactionId=external_tx_id,
            orderId=external_order_id,
            reviewStatus="pending review"
        ))
        
        # Fire-and-forget the task to process external review via the helper function.
        asyncio.create_task(process_entity(external_order_id, external_tx_id))
        # TODO: Consider monitoring and error handling for asynchronous tasks.

    response = CreateTransactionsResponse(status="success", processed=processed_results)
    return jsonify(response.__dict__), 201

# GET endpoint to retrieve transactions.
@app.route('/transactions', methods=['GET'])
async def get_transactions():
    items = entity_service.get_items(
        token=cyoda_token,
        entity_model="transactions",
        entity_version=ENTITY_VERSION
    )
    return jsonify({"transactions": items})

# GET endpoint to retrieve orders.
@app.route('/orders', methods=['GET'])
async def get_orders():
    items = entity_service.get_items(
        token=cyoda_token,
        entity_model="orders",
        entity_version=ENTITY_VERSION
    )
    return jsonify({"orders": items})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
------------------------------------------------

Notes:

1. The startup() function initializes the external cyoda infrastructure.
2. For each new transaction and associated order, we call entity_service.add_item and include the external id in the response.
3. The GET endpoints now retrieve data by calling entity_service.get_items.
4. In process_entity(), after simulating the external review process, we retrieve the current order object, update it, and persist the change via entity_service.update_item.
5. All business logic (data ingestion, external API call simulation, review processing, etc.) is preserved.
6. If additional external service calls (or more operations such as conditions, deletion, etc.) are needed later, you can use the other entity_service functions listed in your instructions.

This refactor replaces the in‑memory dictionaries with external service calls while keeping the core endpoint routes and business logic intact.