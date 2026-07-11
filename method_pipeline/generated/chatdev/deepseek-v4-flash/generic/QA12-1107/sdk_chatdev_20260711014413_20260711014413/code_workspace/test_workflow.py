"""
Integration test for the OMS backend using FastAPI TestClient.
Verifies the full workflow including invoice status updates on payment.
Updated to work with async queue processing: write endpoints return 202,
tests wait for queue drain and verify results via GET endpoints.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from httpx import ASGITransport, AsyncClient
from app.database import init_db
from app.main import create_app, lifespan, queue_mgr


async def wait_for_queue():
    """Wait for the async queue to drain before proceeding."""
    await queue_mgr.join()
    # Small extra yield to let any pending DB writes settle
    await asyncio.sleep(0.05)


async def test_full_workflow():
    """Test the complete order workflow from placement to closure."""
    # Initialize database tables before starting
    await init_db()

    app = create_app()

    # Manually enter the lifespan context so queue, degradation, and state
    # managers are properly started (ASGITransport does not trigger lifespan).
    async with lifespan(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Health check
            resp = await client.get("/health/live")
            assert resp.status_code == 200, f"Health check failed: {resp.text}"
            resp = await client.get("/health/ready")
            assert resp.status_code == 200, f"Ready check failed: {resp.text}"
            print("✅ Health checks passed")

            # 2. Create customer
            resp = await client.post("/api/v1/customers", json={
                "name": "Alice",
                "address": "123 Main St",
                "phone": "555-0100",
                "banking_details": "ACC-12345"
            })
            assert resp.status_code == 201, f"Create customer failed: {resp.text}"
            cust = resp.json()
            customer_id = cust["id"]
            print(f"✅ Customer created: {customer_id}")

            # 3. Create product
            resp = await client.post("/api/v1/products", json={
                "name": "Widget",
                "base_price": 19.99,
                "stock_quantity": 100
            })
            assert resp.status_code == 201, f"Create product failed: {resp.text}"
            prod = resp.json()
            product_id = prod["id"]
            print(f"✅ Product created: {product_id}")

            # 4. Place order (Step 1) — now returns 202 Accepted
            resp = await client.post("/api/v1/orders", json={
                "customer_id": customer_id,
                "items": [{"product_id": product_id, "quantity": 2}]
            })
            assert resp.status_code == 202, f"Place order failed: {resp.text}"
            print(f"✅ Order queued: {resp.json()}")
            await wait_for_queue()

            # Retrieve the order to get its ID and verify status
            resp = await client.get("/api/v1/orders", params={"limit": 1})
            assert resp.status_code == 200, f"List orders failed: {resp.text}"
            orders_data = resp.json()
            assert len(orders_data["orders"]) > 0, "No orders found after placement"
            order = orders_data["orders"][0]
            order_id = order["id"]
            assert order["status"] == "PENDING"
            print(f"✅ Order placed: {order_id}, status: {order['status']}")

            # 5. Review order (Step 2a)
            resp = await client.put(f"/api/v1/orders/{order_id}/review")
            assert resp.status_code == 200, f"Review order failed: {resp.text}"
            order = resp.json()
            assert order["status"] == "REVIEWED"
            print(f"✅ Order reviewed: {order['status']}")

            # 6. Accept order (Step 2b)
            resp = await client.put(f"/api/v1/orders/{order_id}/accept")
            assert resp.status_code == 200, f"Accept order failed: {resp.text}"
            order = resp.json()
            assert order["status"] == "ACCEPTED"
            print(f"✅ Order accepted: {order['status']}")

            # 7. Create invoice (Step 3) — now returns 202 Accepted
            resp = await client.post("/api/v1/invoices", json={
                "order_id": order_id,
                "billing_info": "Invoice for Alice - Widget x2"
            })
            assert resp.status_code == 202, f"Create invoice failed: {resp.text}"
            print(f"✅ Invoice queued: {resp.json()}")
            await wait_for_queue()

            # Retrieve the invoice to get its ID and verify status
            resp = await client.get("/api/v1/invoices", params={"limit": 1})
            assert resp.status_code == 200, f"List invoices failed: {resp.text}"
            inv_data = resp.json()
            assert len(inv_data["invoices"]) > 0, "No invoices found after creation"
            inv = inv_data["invoices"][0]
            invoice_id = inv["id"]
            assert inv["status"] == "ISSUED"
            print(f"✅ Invoice created: {invoice_id}, status: {inv['status']}")

            # 8. Process payment (Step 4) — now returns 202 Accepted
            resp = await client.post("/api/v1/payments", json={
                "order_id": order_id,
                "amount": 39.98,
                "method": "CREDIT_CARD"
            })
            assert resp.status_code == 202, f"Process payment failed: {resp.text}"
            print(f"✅ Payment queued: {resp.json()}")
            await wait_for_queue()

            # Retrieve the payment to get its ID and verify status
            resp = await client.get("/api/v1/payments", params={"limit": 1})
            assert resp.status_code == 200, f"List payments failed: {resp.text}"
            pay_data = resp.json()
            assert len(pay_data["payments"]) > 0, "No payments found after processing"
            pay = pay_data["payments"][0]
            payment_id = pay["id"]
            assert pay["status"] == "COMPLETED"
            print(f"✅ Payment processed: {payment_id}, status: {pay['status']}")

            # 9. Verify invoice status was updated by payment processing
            resp = await client.get(f"/api/v1/invoices/{invoice_id}")
            assert resp.status_code == 200, f"Get invoice failed: {resp.text}"
            inv_after = resp.json()
            print(f"   Invoice status: {inv_after['status']}, paid_at: {inv_after.get('paid_at')}")
            assert inv_after["status"] == "PAID", f"Invoice should be PAID but got {inv_after['status']}"
            assert inv_after.get("paid_at") is not None, "Invoice paid_at should be set"
            print("✅ Invoice correctly marked as PAID after payment")

            # 10. Verify payment (Step 5)
            resp = await client.put(f"/api/v1/payments/{payment_id}/verify")
            assert resp.status_code == 200, f"Verify payment failed: {resp.text}"
            pay = resp.json()
            assert pay["status"] == "COMPLETED"
            print(f"✅ Payment verified: {pay['status']}")

            # 11. Ship order (Step 6)
            resp = await client.put(f"/api/v1/orders/{order_id}/ship")
            assert resp.status_code == 200, f"Ship order failed: {resp.text}"
            order = resp.json()
            assert order["status"] == "SHIPPED"
            print(f"✅ Order shipped: {order['status']}")

            # 12. Close order (Step 7)
            resp = await client.put(f"/api/v1/orders/{order_id}/close")
            assert resp.status_code == 200, f"Close order failed: {resp.text}"
            order = resp.json()
            assert order["status"] == "CLOSED"
            print(f"✅ Order closed: {order['status']}")

            # 13. Final state verification
            resp = await client.get(f"/api/v1/orders/{order_id}")
            assert resp.status_code == 200
            order = resp.json()
            print(f"\n📋 Final Order: {json.dumps(order, indent=2)}")
            assert order["status"] == "CLOSED"
            assert order["invoice_id"] == invoice_id

            print("\n🎉 All tests passed!")


if __name__ == "__main__":
    asyncio.run(test_full_workflow())
