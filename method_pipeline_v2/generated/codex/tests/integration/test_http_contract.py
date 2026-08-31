import httpx
from fastapi import FastAPI
from datetime import UTC, datetime, timedelta

from app.api.routes import customers, invoices, orders, payments, products
from app.core.errors import install_exception_handlers


def build_test_app(session_factory, cache) -> FastAPI:
    app = FastAPI()
    app.state.session_factory = session_factory
    app.state.cache = cache
    install_exception_handlers(app)
    app.include_router(customers.router, prefix="/api/v1")
    app.include_router(products.router, prefix="/api/v1")
    app.include_router(orders.router, prefix="/api/v1")
    app.include_router(invoices.router, prefix="/api/v1")
    app.include_router(payments.router, prefix="/api/v1")
    return app


async def test_manifest_creation_and_get_contract(session_factory, cache) -> None:
    transport = httpx.ASGITransport(app=build_test_app(session_factory, cache))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        invalid = await client.post(
            "/api/v1/customers",
            json={
                "name": "A",
                "address": "12345",
                "phone": "+12345678",
                "bankingDetails": {"accountNumber": "123456", "bankName": "AB"},
                "role": "CUSTOMER",
                "orderHistory": [],
            },
        )
        assert invalid.status_code == 400

        created = await client.post(
            "/api/v1/products",
            json={"description": "ABC", "price": {"amount": "10.00", "currency": "USD"}},
        )
        assert created.status_code == 201
        body = created.json()
        assert body["price"]["amount"] == "10.00"
        fetched = await client.get(f"/api/v1/products/{body['id']}")
        assert fetched.status_code == 200
        missing = await client.get("/api/v1/products/00000000-0000-4000-8000-000000000000")
        assert missing.status_code == 404
        malformed = await client.get("/api/v1/products/not-a-uuid")
        assert malformed.status_code == 400


async def test_complete_workflow_through_versioned_http_routes(session_factory, cache) -> None:
    transport = httpx.ASGITransport(app=build_test_app(session_factory, cache))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        customer_response = await client.post(
            "/api/v1/customers",
            json={
                "name": "Nguyen Van A",
                "address": "123 Nguyen Trai, Hanoi",
                "phone": "+84912345678",
                "bankingDetails": {"accountNumber": "1234567890", "bankName": "Vietcombank"},
                "role": "CUSTOMER",
                "orderHistory": [],
            },
        )
        assert customer_response.status_code == 201
        customer = customer_response.json()
        product_response = await client.post(
            "/api/v1/products",
            json={"description": "Wireless Mouse", "price": {"amount": "100.00", "currency": "USD"}},
        )
        assert product_response.status_code == 201
        product = product_response.json()
        order_response = await client.post(
            "/api/v1/orders",
            json={
                "customerRef": customer["id"],
                "lineItems": [{"productRef": product["id"], "quantity": 1}],
            },
        )
        assert order_response.status_code == 201
        order = order_response.json()
        assert order["status"] == "PLACED"
        assert (await client.post(f"/api/v1/orders/{order['id']}/accept")).json()["order"]["status"] == "ACCEPTED"

        issue_date = datetime.now(UTC).date()
        invoice_response = await client.post(
            "/api/v1/invoices",
            json={
                "orderRef": order["id"],
                "billingInfo": {"name": customer["name"]},
                "issueDate": issue_date.strftime("%d/%m/%Y"),
                "dueDate": (issue_date + timedelta(days=7)).strftime("%d/%m/%Y"),
            },
        )
        assert invoice_response.status_code == 201
        invoice = invoice_response.json()
        assert invoice["totalAmount"] == "100.00"
        payment_response = await client.post(
            "/api/v1/payments",
            json={"orderRef": order["id"], "amount": "100.00", "method": "CREDIT_CARD"},
        )
        assert payment_response.status_code == 201
        payment = payment_response.json()
        verified = await client.post(f"/api/v1/payments/{payment['id']}/verify")
        assert verified.status_code == 200
        assert verified.json()["order"]["status"] == "VERIFIED"
        assert (await client.post(f"/api/v1/orders/{order['id']}/ship")).json()["order"]["status"] == "SHIPPED"
        assert (await client.post(f"/api/v1/orders/{order['id']}/close")).json()["order"]["status"] == "CLOSED"
