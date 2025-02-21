#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import uuid
import datetime
from dataclasses import dataclass, field
from typing import List, Optional
import aiohttp

from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request, validate_response

# Import external entity service functions and constants
# (Assumed to be responsible for persisting data with support for workflow functions)
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # One‐line initialization of schema validation

# ------------------------------------------------------------------------------
# Startup/Initialization: No local in-memory caches; all data is stored externally.
# ------------------------------------------------------------------------------
@app.before_serving
async def startup():
    try:
        await init_cyoda(cyoda_token)
    except Exception as e:
        # Log startup error (in production, use an appropriate logging mechanism)
        print(f"Error initializing cyoda: {e}")
        raise

# ------------------------------------------------------------------------------
# Data Models for Requests and Responses
#
# These data models are used by quart_schema to validate incoming JSON requests.
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
# POST Endpoint for Creating Transactions and Corresponding Orders
#
# For each transaction, we:
# 1. Validate/assign transactionId and timestamp.
# 2. Invoke entity_service.add_item with process_transactions as workflow function.
# 3. Create a corresponding order (with a generated orderId) and call add_item with
#    process_orders as workflow function. The process_orders workflow executes the
#    external review call synchronously before data is persisted.
# ------------------------------------------------------------------------------
@app.route('/transactions', methods=['POST'])
@validate_request(TransactionsWrapper)
@validate_response(CreateTransactionsResponse, 201)
async def create_transactions(data: TransactionsWrapper):
    processed_results = []

    for tx in data.transactions:
        # Ensure each transaction has a unique transactionId.
        internal_id = tx.transactionId or str(uuid.uuid4())
        tx.transactionId = internal_id

        # Set the timestamp if not provided.
        tx.timestamp = tx.timestamp or datetime.datetime.utcnow().isoformat()

        # Convert dataclass instance to dictionary.
        tx_dict = tx.__dict__

        # Call add_item for transactions with the workflow function.
        try:
            external_tx_id = entity_service.add_item(
                token=cyoda_token,
                entity_model="transactions",
                entity_version=ENTITY_VERSION,
                entity=tx_dict,
                workflow=process_transactions
            )
        except Exception as e:
            # If adding a transaction fails, log and skip to next transaction.
            print(f"Error persisting transaction {internal_id}: {e}")
            continue

        # Create an associated order with initial state.
        order_id = str(uuid.uuid4())
        order_data = {
            "orderId": order_id,  # local order id; external service may assign an official one.
            "transactionId": external_tx_id,
            "reviewStatus": "pending review",
            "requestedAt": datetime.datetime.utcnow().isoformat()
        }
        try:
            external_order_id = entity_service.add_item(
                token=cyoda_token,
                entity_model="orders",
                entity_version=ENTITY_VERSION,
                entity=order_data,
                workflow=process_orders
            )
        except Exception as e:
            # If order addition fails, log error and rollback if needed.
            print(f"Error persisting order {order_id}: {e}")
            continue

        # Append the processed result. Note that reviewStatus may have been updated by process_orders.
        processed_results.append(ProcessedResult(
            transactionId=external_tx_id,
            orderId=external_order_id,
            reviewStatus=order_data.get("reviewStatus", "pending review")
        ))

    response = CreateTransactionsResponse(status="success", processed=processed_results)
    return jsonify(response.__dict__), 201

# ------------------------------------------------------------------------------
# GET Endpoint to Retrieve Transactions
# ------------------------------------------------------------------------------
@app.route('/transactions', methods=['GET'])
async def get_transactions():
    try:
        items = entity_service.get_items(
            token=cyoda_token,
            entity_model="transactions",
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        print(f"Error retrieving transactions: {e}")
        items = []
    return jsonify({"transactions": items})

# ------------------------------------------------------------------------------
# GET Endpoint to Retrieve Orders
# ------------------------------------------------------------------------------
@app.route('/orders', methods=['GET'])
async def get_orders():
    try:
        items = entity_service.get_items(
            token=cyoda_token,
            entity_model="orders",
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        print(f"Error retrieving orders: {e}")
        items = []
    return jsonify({"orders": items})

# ------------------------------------------------------------------------------
# Main Entrypoint: Run the Quart application.
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    # Use production-ready logging and configuration for production use.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)