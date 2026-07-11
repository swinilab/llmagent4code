"""
Seed script to populate the database with test data for load testing.
Run before executing locust tests.

Usage:
    python -m oms.load_test.seed_data
"""
import asyncio
import uuid
from decimal import Decimal

from oms.infrastructure.database import database, init_db
from oms.infrastructure.orm_models import (
    CustomerModel,
    ProductModel,
)


async def seed_test_data(
    num_customers: int = 1000,
    num_products: int = 100,
) -> dict:
    """
    Seed the database with test customers and products.
    Returns a dict with the IDs of created entities for use in load tests.
    """
    await init_db()

    async with database.session() as session:
        # Create test customers
        customer_ids = []
        for i in range(num_customers):
            cid = str(uuid.uuid4())
            customer = CustomerModel(
                id=cid,
                name=f"Load Test Customer {i}",
                address=f"{i} Test Street, Testville",
                phone=f"555-{i:04d}",
                banking_details=f"ACC-LOADTEST-{i:04d}",
                role="CUSTOMER",
            )
            session.add(customer)
            customer_ids.append(cid)

        # Create test products
        product_ids = []
        descriptions = [
            "widget", "gadget", "tool", "device", "component",
            "accessory", "part", "supply", "material", "equipment",
        ]
        for i in range(num_products):
            pid = str(uuid.uuid4())
            desc = f"{descriptions[i % len(descriptions)]}-{i}"
            product = ProductModel(
                id=pid,
                description=desc,
                base_price=Decimal(str(round(5.0 + (i * 0.99), 2))),
                currency="USD",
                stock_available=True,
            )
            session.add(product)
            product_ids.append(pid)

        await session.flush()

    return {
        "customer_ids": customer_ids,
        "product_ids": product_ids,
        "num_customers": num_customers,
        "num_products": num_products,
    }


if __name__ == "__main__":
    result = asyncio.run(seed_test_data())
    print(f"Seeded {result['num_customers']} customers and {result['num_products']} products.")
    print(f"Sample customer ID: {result['customer_ids'][0]}")
    print(f"Sample product ID: {result['product_ids'][0]}")
