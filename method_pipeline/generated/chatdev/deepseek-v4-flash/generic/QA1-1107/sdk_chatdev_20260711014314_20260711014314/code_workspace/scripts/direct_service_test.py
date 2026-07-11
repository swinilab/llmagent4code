"""
Quick integration test that directly tests the services without a running server.
"""
import asyncio
import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import async_session_factory, init_db
from app.models.customer import Customer
from app.models.product import Product
from app.enums import CustomerRole, OrderStatus, PaymentMethod
from app.services.order_service import OrderService
from app.services.invoice_service import InvoiceService
from app.services.payment_service import PaymentService
from app.schemas.order import OrderCreate, OrderLineItemCreate
from app.schemas.invoice import InvoiceCreate
from app.schemas.payment import PaymentCreate
from app.workflows.order_workflow import OrderWorkflow


async def test_workflow():
    await init_db()
    async with async_session_factory() as session:
        print("=" * 60)
        print("OMS Complete Workflow Test (Direct Service Test)")
        print("=" * 60)

        # Setup: Create customer and product
        print("\n[Setup] Creating customer and product...")
        customer = Customer(
            name="Test Customer",
            address="123 Test St",
            phone="+1-555-TEST",
            banking_details={"bank": "Test Bank", "account": "TEST123"},
            role=CustomerRole.CUSTOMER,
        )
        session.add(customer)

        product = Product(
            description="Test Product - Widget",
            pricing={"base_price": 49.99, "currency": "USD"},
        )
        session.add(product)
        await session.flush()
        print(f"  Customer: {customer.id}")
        print(f"  Product: {product.id}")

        # Step 1: Place order (using workflow)
        print("\n[Step 1] Customer places order...")
        order_data = OrderCreate(
            customer_id=customer.id,
            line_items=[
                OrderLineItemCreate(
                    product_id=product.id,
                    product_description=product.description,
                    quantity=2,
                    unit_price=49.99,
                    currency="USD",
                )
            ],
            notes="Please handle with care",
        )
        order = await OrderWorkflow.place_order(session, order_data)
        print(f"  Order: {order.id} - Status: {order.status.value}")
        print(f"  Total: ${order.total_amount}")

        # Step 2a: Review order (using workflow)
        print("\n[Step 2a] Order Staff reviews order...")
        order = await OrderWorkflow.review_order(session, order.id)
        print(f"  Order reviewed: Status -> {order.status.value}")

        # Step 2b: Accept order (using workflow)
        print("\n[Step 2b] Order Staff accepts order...")
        order = await OrderWorkflow.accept_order(session, order.id)
        print(f"  Order accepted: Status -> {order.status.value}")

        # Step 3: Create and issue invoice (using workflow)
        print("\n[Step 3] Accountant creates invoice...")
        today = date.today()
        due = today + timedelta(days=30)
        invoice = await OrderWorkflow.create_and_issue_invoice(
            session,
            order_id=order.id,
            billing_info={
                "customer_name": customer.name,
                "customer_address": customer.address,
            },
            issue_date=today,
            due_date=due,
        )
        print(f"  Invoice created: {invoice.id} - #{invoice.invoice_number}")
        print(f"  Invoice Status: {invoice.status.value}")

        # Check order status updated to INVOICED
        order = await OrderService.get_by_id(session, order.id)
        print(f"  Order status after invoicing: {order.status.value}")

        # Step 4: Pay invoice (using workflow)
        print("\n[Step 4] Customer pays invoice...")
        payment = await OrderWorkflow.pay_invoice(
            session,
            order_id=order.id,
            amount=order.total_amount,
            method=PaymentMethod.CREDIT_CARD,
            transaction_ref="TXN-TEST-001",
        )
        print(f"  Payment created: {payment.id} - Status: {payment.status.value}")

        # Step 5: Verify payment (using workflow)
        print("\n[Step 5] Accountant verifies payment...")
        payment = await OrderWorkflow.verify_payment(session, payment.id)
        print(f"  Payment verified: Status -> {payment.status.value}")

        # Check order status updated to PAID
        order = await OrderService.get_by_id(session, order.id)
        print(f"  Order status after payment: {order.status.value}")

        # Check invoice marked as paid
        invoice = await InvoiceService.get_by_id(session, invoice.id)
        print(f"  Invoice status after payment: {invoice.status.value}")

        # Step 6: Ship order (using workflow)
        print("\n[Step 6] Order Staff ships order...")
        order = await OrderWorkflow.ship_order(session, order.id)
        print(f"  Order shipped: Status -> {order.status.value}")

        # Step 7: Close order (using workflow)
        print("\n[Step 7] Order Staff closes order...")
        order = await OrderWorkflow.close_order(session, order.id)
        print(f"  Order closed: Status -> {order.status.value}")

        await session.commit()

        print("\n" + "=" * 60)
        print("WORKFLOW COMPLETED SUCCESSFULLY!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_workflow())
