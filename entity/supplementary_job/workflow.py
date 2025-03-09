def process_fetch_entities(entity):
    """
    Fetch pets, orders, and users from the provided entity data.
    """
    try:
        pets = entity['result']['data']['pets']
        orders = entity['result']['data']['orders']
        users = entity['result']['data']['users']
        
        print(f"Fetched Pets: {pets}")
        print(f"Fetched Orders: {orders}")
        print(f"Fetched Users: {users}")
        
        # Transition to the next state (entities_fetched)
        return {"status": "entities_fetched", "data": {"pets": pets, "orders": orders, "users": users}}
    except Exception as e:
        print(f"Error fetching entities: {e}")
        return {"status": "error", "message": str(e)}

def process_create_summary(entity):
    """
    Create a summary based on the fetched entities.
    """
    try:
        data = entity['result']['data']
        summary = {
            "petCount": len(data['pets']),
            "orderCount": len(data['orders']),
            "userCount": len(data['users'])
        }
        
        print(f"Created Summary: {summary}")
        
        # Transition to the next state (summary_created)
        return {"status": "summary_created", "summary": summary}
    except Exception as e:
        print(f"Error creating summary: {e}")
        return {"status": "error", "message": str(e)}

def process_verify_job(entity):
    """
    Verify job details based on the summary created.
    """
    try:
        summary = entity['summary']
        
        # Implement verification logic here, e.g., checking if counts are valid
        if summary['petCount'] > 0 and summary['orderCount'] > 0 and summary['userCount'] > 0:
            print("Job verified successfully.")
            return {"status": "job_verified"}
        else:
            print("Job verification failed.")
            return {"status": "error", "message": "Invalid counts in summary."}
    except Exception as e:
        print(f"Error verifying job: {e}")
        return {"status": "error", "message": str(e)}

def process_complete_job(entity):
    """
    Finalize job processing.
    """
    try:
        # Implement finalization logic here, such as updating the database or notifying users.
        print("Job completed successfully.")
        
        # Transition to the next state (job_completed)
        return {"status": "job_completed"}
    except Exception as e:
        print(f"Error completing job: {e}")
        return {"status": "error", "message": str(e)}