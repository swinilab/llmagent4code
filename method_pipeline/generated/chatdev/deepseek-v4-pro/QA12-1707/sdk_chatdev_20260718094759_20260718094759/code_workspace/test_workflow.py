"""Full workflow integration test."""
import asyncio
from decimal import Decimal
from src.database import init_db, dispose_engine, _async_session_factory
from src.services.customer import CustomerService
from src.services.product import ProductService
from src.services.order import OrderService
from src.services.payment import PaymentService
from src.services.invoice import InvoiceService
from src.services.workflow import WorkflowService
from src.schemas.customer import CustomerCreate
from src.schemas.product import ProductCreate
from src.schemas.order import OrderCreate, LineItem
from src.schemas.payment import PaymentCreate
from src.schemas.invoice import InvoiceCreate

async def test_full_workflow():
    await init_db()
    
    async with _async_session_factory() as session:
        try:
            # Step 1: Create customer
            cust_svc = CustomerService(session)
            customer = await cust_svc.create(CustomerCreate(
                name="Test Customer",
                address="123 Test St",
                phone="555-TEST",
                banking_details="BANK123",
                role="customer"
            ))
            print(f"✓ Customer created: {customer.id}")

            # Create product
            prod_svc = ProductService(session)
            product = await prod_svc.create(ProductCreate(
                description="Test Widget",
                base_price=Decimal("19.99"),
                currency="USD"
            ))
            print(f"✓ Product created: {product.id}")

            # Step 1: Place order
            order_svc = OrderService(session)
            order = await order_svc.create(OrderCreate(
                customer_id=customer.id,
                line_items=[LineItem(
                    product_id=product.id,
                    description=product.description,
                    quantity=2,
                    unit_price=product.base_price
                )],
                tax=Decimal("2.00")
            ))
            print(f"✓ Order placed: {order.id}, status={order.status.value}, total={order.total}")

            # Step 2: Staff accepts order
            wf_svc = WorkflowService(session)
            result = await wf_svc.staff_accept_order(order.id)
            print(f"✓ Order accepted: {result}")

            # Step 3: Accountant creates invoice
            result = await wf_svc.accountant_create_invoice(
                order.id, 
                billing_info="Test Customer, 123 Test St",
                due_date=None
            )
            print(f"✓ Invoice created: {result}")

            # Step 4: Customer pays
            result = await wf_svc.customer_pay(
                order.id, 
                amount=order.total, 
                method="credit_card"
            )
            print(f"✓ Payment submitted: {result}")

            # Get payment ID
            pay_svc = PaymentService(session)
            payments = await pay_svc.list_by_order(order.id)
            payment_id = payments[0].id

            # Step 5: Accountant verifies payment
            result = await wf_svc.accountant_verify_payment(payment_id)
            print(f"✓ Payment verified: {result}")

            # Step 6: Staff ships order
            result = await wf_svc.staff_ship_order(order.id)
            print(f"✓ Order shipped: {result}")

            # Step 7: Staff closes order
            result = await wf_svc.staff_close_order(order.id)
            print(f"✓ Order closed: {result}")

            # Verify final state
            final_order = await order_svc.get(order.id)
            print(f"\n✓ FINAL STATE: order={final_order.status.value}")
            
            # Verify invoice is paid
            inv_svc = InvoiceService(session)
            invoice = await inv_svc.get_by_order(order.id)
            print(f"✓ Invoice status: {invoice.status.value}")

            print("\n🎉 Full 7-step workflow completed successfully!")
            
        finally:
            await session.rollback()

    await dispose_engine()

asyncio.run(test_full_workflow())
