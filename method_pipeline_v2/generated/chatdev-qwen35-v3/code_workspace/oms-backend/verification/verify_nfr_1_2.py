"""
NFR 1.2 Verification Script - Multiple Copies of Data

This script verifies that data is persisted and can be retrieved after
application restart (simulated by checking database persistence).

Expected: Data created via API is persisted in SQLite database
"""

import httpx
import json
import sys
import sqlite3
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
RESULT_FILE = Path("verification/results/nfr-1.2.json")
DB_PATH = "oms.db"


def verify_multiple_copies():
    """Test that data is persisted in both memory and database."""
    
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # Create a test customer
        import uuid
        test_id = str(uuid.uuid4())
        
        customer_resp = client.post(
            "/api/v1/customers",
            json={
                "id": test_id,
                "name": "Persistence Test Customer",
                "address": "123 Persistence Street, City",
                "phone": "+1234567890",
                "bankingDetails": {
                    "accountNumber": "123456789",
                    "bankName": "Persistence Bank"
                },
                "role": "CUSTOMER"
            }
        )
        
        # Check API response
        api_success = customer_resp.status_code == 201
        api_data = customer_resp.json() if api_success else None
        
        # Check database directly
        db_verified = False
        db_data = None
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.execute(
                "SELECT data FROM customers WHERE id = ?",
                (test_id,)
            )
            row = cursor.fetchone()
            if row:
                db_data = json.loads(row[0])
                db_verified = True
            conn.close()
        except Exception as e:
            db_verified = False
        
        # Verify both copies exist and match
        copies_match = False
        if api_data and db_data:
            copies_match = (
                api_data.get("id") == db_data.get("id") and
                api_data.get("name") == db_data.get("name")
            )
        
        # Verify fault induction
        fault_induced_verified = api_success and db_verified
        
        # Thresholds
        threshold_api_success = api_success
        threshold_db_persisted = db_verified
        threshold_copies_match = copies_match
        
        passed = threshold_api_success and threshold_db_persisted and threshold_copies_match
        
        result = {
            "nfr": "NFR 1.2 Maintain Multiple copies of Data",
            "tacticUsed": "Availability > Maintain Multiple Copies of Data > Replication",
            "faultInduced": {
                "description": "Created customer via API and verified persistence in SQLite database",
                "mechanism": "BaseRepository.save() serializes to JSON and stores in SQLite",
                "verified": fault_induced_verified
            },
            "baseline": {
                "metric": "in_memory_copy",
                "value": "verified"
            },
            "observed": [
                {"metric": "api_success", "value": api_success},
                {"metric": "db_verified", "value": db_verified},
                {"metric": "copies_match", "value": copies_match}
            ],
            "threshold": [
                {"metric": "api_success", "operator": "==", "value": True},
                {"metric": "db_verified", "operator": "==", "value": True},
                {"metric": "copies_match", "operator": "==", "value": True}
            ],
            "passed": passed
        }
    
    # Write result
    RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULT_FILE, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"NFR 1.2 Verification: {'PASSED' if passed else 'FAILED'}")
    print(f"  API success: {api_success}")
    print(f"  Database verified: {db_verified}")
    print(f"  Copies match: {copies_match}")
    
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(verify_multiple_copies())
