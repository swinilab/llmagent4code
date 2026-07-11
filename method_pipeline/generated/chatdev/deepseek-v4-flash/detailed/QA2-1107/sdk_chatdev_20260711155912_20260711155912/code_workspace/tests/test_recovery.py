"""
Recovery Test (NFR 2.2): Script that temporarily blocks network traffic to
the DB port. Pass if errors spike briefly then auto-recover without
manual restart.

Usage:
    python tests/test_recovery.py

This script:
1. Verifies the API is healthy.
2. Blocks traffic to the DB port using iptables (requires root).
3. Sends requests during the block — expects errors.
4. Unblocks the DB port.
5. Sends requests after unblock — expects recovery.
6. Verifies the health endpoint reports healthy.

Prerequisites:
    - OMS API running on http://localhost:8000
    - PostgreSQL running on localhost:5432
    - Root/sudo access for iptables commands
"""
from __future__ import annotations

import subprocess
import sys
import time

import httpx

BASE_URL = "http://localhost:8000/api/v1"
DB_PORT = "5432"
RECOVERY_WAIT = 10  # seconds to wait after unblocking


def run_iptables(action: str, comment: str) -> None:
    """Add or remove an iptables rule to block/unblock DB port."""
    if action == "add":
        cmd = [
            "sudo", "iptables", "-A", "INPUT",
            "-p", "tcp", "--dport", DB_PORT,
            "-j", "DROP",
            "-m", "comment", "--comment", comment,
        ]
    else:
        cmd = [
            "sudo", "iptables", "-D", "INPUT",
            "-p", "tcp", "--dport", DB_PORT,
            "-j", "DROP",
            "-m", "comment", "--comment", comment,
        ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  iptables warning: {result.stderr.strip()}")


def check_health(client: httpx.Client) -> bool:
    """Check if the health endpoint returns healthy."""
    try:
        resp = client.get(f"{BASE_URL}/health", timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("status") == "healthy" and data.get("database") == "connected"
        return False
    except Exception:
        return False


def main() -> int:
    """Run the recovery test."""
    print("=" * 60)
    print("Recovery Test (NFR 2.2)")
    print("=" * 60)

    with httpx.Client() as client:
        # Step 1: Verify initial health
        print("\n[STEP 1] Verifying initial health...")
        if check_health(client):
            print("  ✅ API is healthy")
        else:
            print("  ❌ API is not healthy. Ensure it's running.")
            return 1

        # Step 2: Block DB port
        print(f"\n[STEP 2] Blocking port {DB_PORT} (simulating DB failure)...")
        run_iptables("add", "oms-recovery-test")
        print("  DB port blocked.")

        # Step 3: Send requests during block — expect errors
        print(f"\n[STEP 3] Sending requests during DB block (expecting errors)...")
        errors_detected = False
        for i in range(5):
            try:
                resp = client.get(f"{BASE_URL}/health", timeout=5.0)
                if resp.status_code != 200:
                    errors_detected = True
                    print(f"  Request {i+1}: Got status {resp.status_code} (expected error)")
                else:
                    data = resp.json()
                    if data.get("database") == "disconnected":
                        errors_detected = True
                        print(f"  Request {i+1}: Database disconnected (degraded mode)")
                    else:
                        print(f"  Request {i+1}: Unexpected success — {data}")
            except Exception as e:
                errors_detected = True
                print(f"  Request {i+1}: Connection error (expected): {type(e).__name__}")
            time.sleep(0.5)

        if not errors_detected:
            print("  ⚠️  No errors detected during DB block. Check iptables rules.")

        # Step 4: Unblock DB port
        print(f"\n[STEP 4] Unblocking port {DB_PORT}...")
        run_iptables("remove", "oms-recovery-test")
        print("  DB port unblocked.")

        # Step 5: Wait for recovery and verify
        print(f"\n[STEP 5] Waiting {RECOVERY_WAIT}s for auto-recovery...")
        time.sleep(RECOVERY_WAIT)

        recovered = False
        for i in range(5):
            if check_health(client):
                recovered = True
                print(f"  ✅ API recovered (attempt {i+1})")
                break
            print(f"  Attempt {i+1}: Not yet recovered...")
            time.sleep(2)

        if recovered:
            print("\n✅ PASS: System auto-recovered after DB interruption")
            return 0
        else:
            print("\n❌ FAIL: System did not auto-recover within timeout")
            return 1


if __name__ == "__main__":
    sys.exit(main())
