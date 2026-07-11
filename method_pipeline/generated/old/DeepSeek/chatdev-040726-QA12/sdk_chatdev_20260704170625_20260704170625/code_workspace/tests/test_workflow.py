"""End-to-end tests for the complete OMS workflow.

Tests the 7-step lifecycle:
1. Customer places order
2. Order Staff reviews & accepts
3. Accountant creates invoice
4. Customer pays invoice
5. Accountant verifies payment
6. Order Staff ships paid order
7. Order Staff closes completed order
"""

from __future__ import annotations

from typing import Any

import pytest
import pytest_asyncio


class TestWorkflow:
    """Full order lifecycle integration test."""

    @pytest.mark.asyncio
    async def test_full_workflow(
        self, client: Any, sample_customer: dict[str, Any], sample_product: dict[str, Any]
    ) -> None:
        cust_id = sample_customer["id"]
        prod_id = sample_product["id"]

        # ── Step 1: Customer places order ─────────────────────────────────────
        resp = await client.post(
            "/v1/orders",
            json={
                "customer_id": cust_id,
                "line_items": [
                    {
                        "product_id": prod_id,
                        "quantity": 3,
                        "unit_price": "29.99",
                        "subtotal": "89.97",
                    }
                ],
            },
        )
        assert resp.status_code == 201
        order = resp.json()
        order_id = order["id"]
        assert order["status"] == "pending"
        assert order["customer_id"] == cust_id

        # ── Step 2: Order Staff accepts order ─────────────────────────────────
        resp = await client.post(f"/v1/orders/{order_id}/accept")
        assert resp.status_code == 200
        assert resp.json()["order"]["status"] == "accepted"

        # ── Step 3: Accountant creates invoice ────────────────────────────────
        resp = await client.post(
            "/v1/invoices",
            json={
                "order_id": order_id,
                "customer_id": cust_id,
                "billing_name": "Alice Johnson",
                "billing_address": "123 Elm St",
                "total_amount": "89.97",
                "due_days": 30,
            },
        )
        assert resp.status_code == 201
        invoice = resp.json()
        invoice_id = invoice["id"]
        assert invoice["status"] == "issued"

        # Order should now be INVOICED
        resp = await client.get(f"/v1/orders/{order_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "invoiced"

        # ── Step 4: Customer pays invoice ─────────────────────────────────────
        # First create a payment
        resp = await client.post(
            "/v1/payments",
            json={
                "order_id": order_id,
                "invoice_id": invoice_id,
                "amount": "89.97",
                "method": "credit_card",
            },
        )
        assert resp.status_code == 201
        payment_id = resp.json()["id"]

        # Pay the invoice
        resp = await client.post(f"/v1/invoices/{invoice_id}/pay")
        assert resp.status_code == 200
        assert resp.json()["invoice"]["status"] == "paid"

        # Order should now be PAID
        resp = await client.get(f"/v1/orders/{order_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "paid"

        # ── Step 5: Accountant verifies payment ───────────────────────────────
        resp = await client.post(f"/v1/payments/{payment_id}/complete")
        assert resp.status_code == 200
        assert resp.json()["payment"]["status"] == "completed"

        # Order should now be VERIFIED
        resp = await client.get(f"/v1/orders/{order_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "verified"

        # ── Step 6: Order Staff ships order ───────────────────────────────────
        resp = await client.post(f"/v1/orders/{order_id}/ship")
        assert resp.status_code == 200
        assert resp.json()["order"]["status"] == "shipped"

        # ── Step 7: Order Staff closes completed order ────────────────────────
        resp = await client.post(f"/v1/orders/{order_id}/close")
        assert resp.status_code == 200
        assert resp.json()["order"]["status"] == "completed"

        # Verify final state
        resp = await client.get(f"/v1/orders/{order_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"


class TestAPIEndpoints:
    """Unit tests for individual API endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: Any) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data

    @pytest.mark.asyncio
    async def test_create_customer(self, client: Any) -> None:
        resp = await client.post(
            "/v1/customers",
            json={
                "name": "Bob",
                "address": "456 Oak Ave",
                "phone": "+1-555-0200",
                "banking_details": "Bank of Test, acct 67890",
                "role": "customer",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Bob"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_customer_not_found(self, client: Any) -> None:
        resp = await client.get("/v1/customers/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_product(self, client: Any) -> None:
        resp = await client.post(
            "/v1/products",
            json={
                "description": "Super Widget",
                "base_price": "49.99",
                "currency": "USD",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["description"] == "Super Widget"
        assert data["base_price"] == "49.99"

    @pytest.mark.asyncio
    async def test_list_products(self, client: Any, sample_product: dict[str, Any]) -> None:
        resp = await client.get("/v1/products")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_place_order_invalid_customer(self, client: Any) -> None:
        resp = await client.post(
            "/v1/orders",
            json={
                "customer_id": "nonexistent",
                "line_items": [],
            },
        )
        # Customer validation now raises ValueError → 400
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_order_status_transitions(self, client: Any, sample_customer: dict[str, Any]) -> None:
        cust_id = sample_customer["id"]

        # Create a product
        resp = await client.post(
            "/v1/products",
            json={
                "description": "Test Widget",
                "base_price": "10.00",
                "currency": "USD",
            },
        )
        assert resp.status_code == 201
        prod_id = resp.json()["id"]

        # Place order
        resp = await client.post(
            "/v1/orders",
            json={
                "customer_id": cust_id,
                "line_items": [
                    {
                        "product_id": prod_id,
                        "quantity": 1,
                        "unit_price": "10.00",
                        "subtotal": "10.00",
                    }
                ],
            },
        )
        assert resp.status_code == 201
        order = resp.json()
        order_id = order["id"]
        assert order["status"] == "pending"

        # Accept
        resp = await client.post(f"/v1/orders/{order_id}/accept")
        assert resp.status_code == 200
        assert resp.json()["order"]["status"] == "accepted"

        # Cannot accept again
        resp = await client.post(f"/v1/orders/{order_id}/accept")
        assert resp.status_code == 409

        # Cannot ship before payment
        resp = await client.post(f"/v1/orders/{order_id}/ship")
        assert resp.status_code == 409

        # Cannot close before shipping
        resp = await client.post(f"/v1/orders/{order_id}/close")
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_invoice_lifecycle(self, client: Any, sample_customer: dict[str, Any], sample_product: dict[str, Any]) -> None:
        cust_id = sample_customer["id"]
        prod_id = sample_product["id"]

        # Create and accept order
        resp = await client.post(
            "/v1/orders",
            json={
                "customer_id": cust_id,
                "line_items": [
                    {
                        "product_id": prod_id,
                        "quantity": 1,
                        "unit_price": "29.99",
                        "subtotal": "29.99",
                    }
                ],
            },
        )
        assert resp.status_code == 201
        order_id = resp.json()["id"]

        resp = await client.post(f"/v1/orders/{order_id}/accept")
        assert resp.status_code == 200

        # Create invoice
        resp = await client.post(
            "/v1/invoices",
            json={
                "order_id": order_id,
                "customer_id": cust_id,
                "billing_name": "Alice",
                "billing_address": "123 St",
                "total_amount": "29.99",
                "due_days": 30,
            },
        )
        assert resp.status_code == 201
        invoice_id = resp.json()["id"]
        assert resp.json()["status"] == "issued"

        # Cannot create invoice again for same order (already invoiced)
        resp = await client.post(
            "/v1/invoices",
            json={
                "order_id": order_id,
                "customer_id": cust_id,
                "billing_name": "Alice",
                "billing_address": "123 St",
                "total_amount": "29.99",
                "due_days": 30,
            },
        )
        assert resp.status_code == 409

        # Get invoice
        resp = await client.get(f"/v1/invoices/{invoice_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == invoice_id

    @pytest.mark.asyncio
    async def test_payment_lifecycle(self, client: Any, sample_customer: dict[str, Any], sample_product: dict[str, Any]) -> None:
        cust_id = sample_customer["id"]
        prod_id = sample_product["id"]

        # Create, accept order, create invoice
        resp = await client.post(
            "/v1/orders",
            json={
                "customer_id": cust_id,
                "line_items": [
                    {
                        "product_id": prod_id,
                        "quantity": 1,
                        "unit_price": "15.00",
                        "subtotal": "15.00",
                    }
                ],
            },
        )
        assert resp.status_code == 201
        order_id = resp.json()["id"]

        resp = await client.post(f"/v1/orders/{order_id}/accept")
        assert resp.status_code == 200

        resp = await client.post(
            "/v1/invoices",
            json={
                "order_id": order_id,
                "customer_id": cust_id,
                "billing_name": "Alice",
                "billing_address": "123 St",
                "total_amount": "15.00",
                "due_days": 30,
            },
        )
        assert resp.status_code == 201
        invoice_id = resp.json()["id"]

        # Create payment
        resp = await client.post(
            "/v1/payments",
            json={
                "order_id": order_id,
                "invoice_id": invoice_id,
                "amount": "15.00",
                "method": "bank_transfer",
            },
        )
        assert resp.status_code == 201
        payment_id = resp.json()["id"]
        assert resp.json()["status"] == "pending"

        # Pay invoice
        resp = await client.post(f"/v1/invoices/{invoice_id}/pay")
        assert resp.status_code == 200
        assert resp.json()["invoice"]["status"] == "paid"

        # Complete payment (verify)
        resp = await client.post(f"/v1/payments/{payment_id}/complete")
        assert resp.status_code == 200
        assert resp.json()["payment"]["status"] == "completed"

        # Cannot complete again
        resp = await client.post(f"/v1/payments/{payment_id}/complete")
        assert resp.status_code == 409

        # List payments
        resp = await client.get("/v1/payments")
        assert resp.status_code == 200
        payments = resp.json()
        assert len(payments) >= 1