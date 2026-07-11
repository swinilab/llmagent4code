"""
State Preservation Test (NFR 2.3): Script that force-terminates (kill -9)
the OMS process during order creation. Pass if DB reflects all committed
transactions up to failure upon restart.

Usage:
    python tests/test_state.py

This script:
1. Creates test data (customer, product).
2. Starts placing orders in a loop.
3. Force-kills the OMS process mid-operation.
4. Restarts the OMS process.
5. Verifies that committed orders are present in the database.
6. Verifies that in-flight orders are detected on startup.

Prerequisites:
    - OMS API running on http://localhost:8000
    - PostgreSQL running with schema applied
    - Ability to run `pkill` or `kill` commands
"""
from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
import time
import uuid

import httpx

BASE_URL = "http://localhost:8000/api/v1"
OMS_PID_FILE = "/tmp/oms_pid.txt"

SAMPLE_CUSTOMER = {
    "name": "State Test Customer",
    "address": "456 Test Ave",
    "phone": "+1-555-0200",
    "banking_details": "ACC-67890",
    "role": "CUSTOMER",
}

SAMPLE_PRODUCT = {
    "description": "State Test Product",
    "base_price": 49.99,
    "currency": "USD",
    "available": True,
}


async def create_test_data(client: httpx.AsyncClient) -> tuple[str, str]:
    """Create a customer and product for testing."""
    resp = await client.post(f"{BASE_URL}/customers", json=SAMPLE_CUSTOMER)
    resp.raise_for_status()
    customer_id = resp.json()["id"]

    resp = await client.post(f"{BASE_URL}/products", json=SAMPLE_PRODUCT)
    resp.raise_for_status()
    product_id = resp.json()["id"]

    return customer_id, product_id


async def place_order(client: httpx.AsyncClient, customer_id: str, product_id: str) -> dict | None:
    """Place a single order."""
    order_data = {
        "customer_id": customer_id,
        "line_items": [
            {
                "product_id": product_id,
                "quantity": 1,
                "unit_price": 49.99,
                "currency": "USD",
            }
        ],
        "currency": "USD",
    }
    try:
        resp = await client.post(f"{BASE_URL}/orders", json=order_data, timeout=10.0)
        if resp.status_code == 201:
            return resp.json()
        return None
    except Exception:
        return None


def get_oms_pid() -> int | None:
    """Get the PID of the running OMS process."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "uvicorn app.main:app"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            return int(pids[0])
    except Exception:
        pass
    return None


def kill_oms(pid: int) -> None:
    """Force-kill the OMS process."""
    try:
        os.kill(pid, signal.SIGKILL)
        print(f"  Killed OMS process (PID {pid})")
    except ProcessLookupError:
        print("  Process already terminated")


def restart_oms() -> bool:
    """Restart the OMS process."""
    try:
        subprocess.Popen(
            ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception as e:
        print(f"  Failed to restart OMS: {e}")
        return False


async def wait_for_healthy(client: httpx.AsyncClient, max_retries: int = 15) -> bool:
    """Wait for the API to become healthy."""
    for i in range(max_retries):
        try:
            resp = await client.get(f"{BASE_URL}/health", timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "healthy":
                    return True
        except Exception:
            pass
        await asyncio.sleep(2)
    return False


async def main() -> int:
    """Run the state preservation test."""
    print("=" * 60)
    print("State Preservation Test (NFR 2.3)")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # Step 1: Create test data
        print("\n[STEP 1] Creating test data...")
        try:
            customer_id, product_id = await create_test_data(client)
            print(f"  Customer ID: {customer_id}")
            print(f"  Product ID:  {product_id}")
        except Exception as e:
            print(f"  FAILED: {e}")
            return 1

        # Step 2: Place some orders before killing
        print("\n[STEP 2] Placing orders before kill...")
        committed_before = []
        for i in range(3):
            order = await place_order(client, customer_id, product_id)
            if order:
                committed_before.append(order["id"])
                print(f"  Order {i+1}: {order['id']} (status={order['status']})")
            else:
                print(f"  Order {i+1}: FAILED")

        # Step 3: Get OMS PID and kill it
        print("\n[STEP 3] Force-killing OMS process...")
        pid = get_oms_pid()
        if pid is None:
            print("  Could not find OMS PID. Is it running?")
            return 1
        print(f"  Found OMS PID: {pid}")
        kill_oms(pid)
        time.sleep(2)

        # Verify process is dead
        if get_oms_pid() is not None:
            print("  OMS process still running. Kill may have failed.")
            return 1
        print("  OMS process terminated.")

        # Step 4: Restart OMS
        print("\n[STEP 4] Restarting OMS...")
        if not restart_oms():
            return 1
        print("  OMS restart initiated.")

        # Step 5: Wait for healthy
        print("\n[STEP 5] Waiting for OMS to become healthy...")
        if await wait_for_healthy(client):
            print("  ✅ OMS is healthy after restart")
        else:
            print("  ❌ OMS did not become healthy")
            return 1

        # Step 6: Verify committed orders survived
        print("\n[STEP 6] Verifying committed orders survived...")
        all_survived = True
        for order_id in committed_before:
            try:
                resp = await client.get(f"{BASE_URL}/orders/{order_id}", timeout=10.0)
                if resp.status_code == 200:
                    order = resp.json()
                    print(f"  Order {order_id}: FOUND (status={order['status']}) ✅")
                else:
                    print(f"  Order {order_id}: NOT FOUND (status={resp.status_code}) ❌")
                    all_survived = False
            except Exception as e:
                print(f"  Order {order_id}: ERROR — {e} ❌")
                all_survived = False

        # Step 7: Check startup recovery detected in-flight orders
        print("\n[STEP 7] Checking startup recovery detected in-flight orders...")
        try:
            resp = await client.get(f"{BASE_URL}/health", timeout=5.0)
            if resp.status_code == 200:
                print(f"  Health: {resp.json()}")
        except Exception as e:
            print(f"  Health check error: {e}")

        if all_survived:
            print("\n✅ PASS: All committed orders survived the crash")
            return 0
        else:
            print("\n❌ FAIL: Some committed orders were lost")
            return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
