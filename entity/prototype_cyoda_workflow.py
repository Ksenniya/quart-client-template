Below is an updated complete version of the file where we’ve moved the asynchronous external review logic (originally implemented as a separate fire‐and‐forget task) into the orders’ workflow function. In other words, the process_orders function now (a) receives the order entity just before it’s persisted, (b) calls the external API asynchronously to compute the review outcome, and (c) updates the order’s state directly (by modifying attributes on the passed-in entity). This removes extra logic from the controller and “frees” our endpoints from asynchronous side–effects.

────────────────────────────────────────────
#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from dataclasses import dataclass, field
from typing import List, Optional
import aiohttp

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_response

# Import external entity service functions and constants
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

# There is no longer an in-memory cache – all data is now stored externally.
# transactions_db = {}
# orders_db = {}

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# ------------------------------------------------------------------------------
# Workflow Functions
#
# Each workflow function is executed asynchronously right before persistence.
# They can perform asynchronous operations and change the entity state directly.
# IMPORTANT: Do not call entity_service.add/update/delete for this same entity.
# ------------------------------------------------------------------------------

async def process_transactions(entity: dict):
    # In this workflow, we could add any extra logic before persisting a transaction.
    # For example, we can mark that the entity has been pre-processed.
    entity["workflowValidated"] = True
    # Additional asynchronous operations can be initiated if necessary.
    # Do not call entity_service operations on the 'transactions' entity.
    return

async def process_orders(entity: dict):
    # Instead of firing off an external asynchronous task from the controller,
    # we incorporate its logic directly into the workflow.
    #
    # Here, we simulate an external review call with aiohttp and update the order.
    #
    # Note: Since this workflow function is applied directly to the order entity,
    # simply modifying its attributes (e.g. entity["reviewStatus"]) is enough.
    async with aiohttp.ClientSession() as session:
        try:
            # Replace the URL and payload with actual external API details.
            external_url = "http://external-review-api/validate"  # Placeholder URL
            payload = {"transactionId": entity.get("transactionId")}
            async with session.post(external_url, json=payload) as resp:
                if resp.status == 200:
                    review_data = await resp.json()
                    outcome = review_data.get("reviewStatus", "approved")
                else:
                    outcome = "failed review"
        except Exception as e:
            # In production, replace print with proper logging.
            print(f"Error calling external API for order {entity.get('orderId')}: {e}")
            outcome = "failed review"
    # Mimic minimal processing delay if required.
    await asyncio.sleep(0.1)
    # Directly update the order entity.
    entity["reviewStatus"] = outcome
    entity["reviewTimestamp"] = datetime.datetime.utcnow().isoformat()
    return

# ------------------------------------------------------------------------------
# Data Models for Requests and Responses
# ------------------------------------------------------------------------------

@dataclass
class TransactionItem:
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

# ------------------------------------------------------------------------------
# POST endpoint for creating transactions
# ------------------------------------------------------------------------------
@app.route('/transactions', methods=['POST'])
@validate_request(TransactionsWrapper)
@validate_response(CreateTransactionsResponse, 201)
async def create_transactions(data: TransactionsWrapper):
    processed_results = []
    for tx in data.transactions:
        # Assign a new transactionId if missing.
        internal_id = tx.transactionId or str(uuid.uuid4())
        tx.transactionId = internal_id
        # Assign a current timestamp if not provided.
        tx.timestamp = tx.timestamp or datetime.datetime.utcnow().isoformat()
        tx_dict = tx.__dict__

        # Call add_item with the transaction workflow function.
        external_tx_id = entity_service.add_item(
            token=cyoda_token,
            entity_model="transactions",
            entity_version=ENTITY_VERSION,
            entity=tx_dict,
            workflow=process_transactions
        )
        
        # Create a corresponding order with initial review status.
        order_id = str(uuid.uuid4())
        order_data = {
            "orderId": order_id,
            "transactionId": external_tx_id,
            "reviewStatus": "pending review",
            "requestedAt": datetime.datetime.utcnow().isoformat()
        }
        # Call add_item with the orders workflow function, which will handle
        # the external review asynchronously before persistence.
        external_order_id = entity_service.add_item(
            token=cyoda_token,
            entity_model="orders",
            entity_version=ENTITY_VERSION,
            entity=order_data,
            workflow=process_orders
        )

        processed_results.append(ProcessedResult(
            transactionId=external_tx_id,
            orderId=external_order_id,
            reviewStatus=order_data["reviewStatus"]
        ))
        # Note: We no longer need to fire off an extra task for review processing.
        # The entire external API call and state update is embedded in process_orders.

    response = CreateTransactionsResponse(status="success", processed=processed_results)
    return jsonify(response.__dict__), 201

# ------------------------------------------------------------------------------
# GET endpoint to retrieve transactions.
# ------------------------------------------------------------------------------
@app.route('/transactions', methods=['GET'])
async def get_transactions():
    items = entity_service.get_items(
        token=cyoda_token,
        entity_model="transactions",
        entity_version=ENTITY_VERSION
    )
    return jsonify({"transactions": items})

# ------------------------------------------------------------------------------
# GET endpoint to retrieve orders.
# ------------------------------------------------------------------------------
@app.route('/orders', methods=['GET'])
async def get_orders():
    items = entity_service.get_items(
        token=cyoda_token,
        entity_model="orders",
        entity_version=ENTITY_VERSION
    )
    return jsonify({"orders": items})

# ------------------------------------------------------------------------------
# Run the Quart App when executed directly.
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
────────────────────────────────────────────

Explanation:

1. Previously, the endpoint fired off a separate asynchronous task (via asyncio.create_task(process_entity(...))) to perform external review processing for orders. Now, all that logic has been moved into the orders’ workflow function (process_orders).  
2. When entity_service.add_item is called with workflow=process_orders, the external API call (using aiohttp) is executed just before the order is persisted. The order’s state (reviewStatus and reviewTimestamp) is then updated on the fly by directly modifying the entity dictionary.
3. The controller (the route create_transactions) is now lighter and does not need to manage any asynchronous side–effects.
4. A similar approach is applied for transactions with process_transactions (which could include any extra pre-persistence logic).

This design centralizes asynchronous logic into the workflow functions and “frees” our controllers from excessive responsibilities while ensuring that every change is applied directly to the entity before it’s persisted.