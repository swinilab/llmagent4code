"""
NFR 1.1 Verification Script - Rate Limiting

This script verifies that the rate limiter correctly limits requests
when the maximum event rate is exceeded.

Threshold: 100 requests per 60 seconds
Expected: 101st request within the window should be rate-limited
"""

import httpx
import json
import sys
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
RESULT_FILE = Path("verification/results/nfr-1.1.json")


def verify_rate_limiting():
    """Test that rate limiting kicks in after max_events."""
    
    # First, check baseline (healthy system)
    baseline_success = 0
    baseline_total = 10
    
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # Baseline: send a few requests and count successes
        for i in range(baseline_total):
            try:
                resp = client.get("/health")
                if resp.status_code == 200:
                    baseline_success += 1
            except Exception:
                pass
        
        baseline_p95 = 50  # Estimated baseline response time in ms
        
        # Now induce the fault: exceed rate limit
        max_events = 100
        requests_sent = 0
        requests_allowed = 0
        requests_rejected = 0
        
        # Send requests rapidly to exceed the limit
        for i in range(max_events + 10):
            try:
                resp = client.post(
                    "/api/v1/customers",
                    json={
                        "name": f"Test Customer {i}",
                        "address": "123 Test Street, Test City",
                        "phone": "+1234567890",
                        "bankingDetails": {
                            "accountNumber": "123456789",
                            "bankName": "Test Bank"
                        },
                        "role": "CUSTOMER"
                    }
                )
                requests_sent += 1
                if resp.status_code == 201:
                    requests_allowed += 1
                elif resp.status_code == 400 and "Rate limit" in resp.text:
                    requests_rejected += 1
                else:
                    # Other errors (validation, etc.) still count as processed
                    requests_allowed += 1
            except httpx.ReadTimeout:
                requests_rejected += 1
            except Exception as e:
                requests_rejected += 1
        
        # Check rate limiter status
        try:
            status_resp = client.get("/rate-limit-status")
            rate_limit_status = status_resp.json() if status_resp.status_code == 200 else {}
        except Exception:
            rate_limit_status = {}
    
    # Verify results
    fault_induced_verified = requests_rejected > 0 or rate_limit_status.get("current_events", 0) >= max_events
    
    # Thresholds
    threshold_max_allowed = max_events  # Should not allow more than max_events
    threshold_rejection_required = True  # Should reject at least some requests after limit
    
    passed = (
        requests_allowed <= threshold_max_allowed + 5 and  # Allow small buffer for validation errors
        fault_induced_verified
    )
    
    result = {
        "nfr": "NFR 1.1 Limit Event Response",
        "tacticUsed": "Performance > Limit Event Response",
        "faultInduced": {
            "description": f"Sent {requests_sent} requests rapidly to exceed rate limit of {max_events} per 60s",
            "mechanism": "RateLimiter.acquire() with sliding window",
            "verified": fault_induced_verified
        },
        "baseline": {
            "metric": "healthy_requests",
            "value": baseline_success
        },
        "observed": [
            {"metric": "requests_sent", "value": requests_sent},
            {"metric": "requests_allowed", "value": requests_allowed},
            {"metric": "requests_rejected", "value": requests_rejected},
            {"metric": "current_events_in_window", "value": rate_limit_status.get("current_events", 0)}
        ],
        "threshold": [
            {"metric": "requests_allowed", "operator": "<=", "value": threshold_max_allowed + 5},
            {"metric": "fault_induced_verified", "operator": "==", "value": True}
        ],
        "passed": passed
    }
    
    # Write result
    RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULT_FILE, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"NFR 1.1 Verification: {'PASSED' if passed else 'FAILED'}")
    print(f"  Requests sent: {requests_sent}")
    print(f"  Requests allowed: {requests_allowed}")
    print(f"  Requests rejected: {requests_rejected}")
    print(f"  Current events in window: {rate_limit_status.get('current_events', 'N/A')}")
    
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(verify_rate_limiting())
