"""Direct test of order service to see the actual error."""
import asyncio
import sys
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_oms2.db"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import async_session_factory, engine, Base
from app.models.customer import Customer
from app.models.product import Product
from app.schemas.order import OrderCreate, OrderLineItemCreate
from app.services.order_service import OrderService
from app.enums import CustomerRole


async def test():
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session_factory() as session:
        # Create a customer
        customer = Customer(
            name="Test",
            address="123 St",
            phone="555",
            banking_details={},
            role=CustomerRole.CUSTOMER,
        )
        session.add(customer)
        await session.flush()
        print(f"Customer: {customer.id}")

        # Create a product
        product = Product(
            description="Test Product",
            pricing={"base_price": 10, "currency": "USD"},
        )
        session.add(product)
        await session.flush()
        print(f"Product: {product.id}")

        # Create order
        try:
            order_data = OrderCreate(
                customer_id=customer.id,
                line_items=[
                    OrderLineItemCreate(
                        product_id=product.id,
                        product_description=product.description,
                        quantity=1,
                        unit_price=10,
                        currency="USD",
                    )
                ],
                notes="Test",
            )
            print(f"Order data: {order_data}")
            order = await OrderService.create(session, order_data)
            print(f"Order created: {order.id}")
            print(f"Order status: {order.status}")
            print(f"Order total: {order.total_amount}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
