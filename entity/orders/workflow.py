async def process_orders(entity: dict):
    """
    Workflow function for 'orders'. This function replaces the previous fire-and-forget
    asynchronous task, executing the external API call to validate the order review
    status immediately before persistence.
    """
    try:
        # Ensure we have the necessary transaction id
        transaction_id = entity.get("transactionId")
        if not transaction_id:
            raise ValueError("Missing transactionId in order entity.")

        async with aiohttp.ClientSession() as session:
            # NOTE: Replace external_url with your actual endpoint!
            external_url = "http://external-review-api/validate"  # Placeholder URL
            payload = {"transactionId": transaction_id}
            try:
                async with session.post(external_url, json=payload) as resp:
                    if resp.status == 200:
                        review_data = await resp.json()
                        # Expecting reviewStatus from external API; fallback to 'approved'
                        outcome = review_data.get("reviewStatus", "approved")
                    else:
                        outcome = "failed review"
            except Exception as api_exception:
                # Log error and use fallback outcome
                print(f"Error during API call in process_orders for order {entity.get('orderId')}: {api_exception}")
                outcome = "failed review"

        # Mimic a minimal processing delay (if necessary for rate limiting or sequencing)
        await asyncio.sleep(0.1)
        # Update the order entity in-place. These modifications will be persisted.
        entity["reviewStatus"] = outcome
        entity["reviewTimestamp"] = datetime.datetime.utcnow().isoformat()

    except Exception as e:
        # In case any general error occurs in the workflow, set a safe state.
        print(f"Error in process_orders workflow: {e}")
        entity["reviewStatus"] = "failed review"
        entity["reviewTimestamp"] = datetime.datetime.utcnow().isoformat()
    return