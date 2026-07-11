"""
Seed script to populate the database with sample data for testing.
Run: uv run python scripts/seed_data.py
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import async_session_factory, init_db
from app.models.customer import Customer
from app.models.product import Product
from app.enums import CustomerRole


async def seed():
    await init_db()
    async with async_session_factory() as session:
        # Create sample customers
        customers = [
            Customer(
                name="Alice Johnson",
                address="123 Main St, Springfield, IL",
                phone="+1-555-0101",
                banking_details={"bank": "Chase", "account": "****1234"},
                role=CustomerRole.CUSTOMER,
            ),
            Customer(
                name="Bob Smith (Staff)",
                address="456 Oak Ave, Springfield, IL",
                phone="+1-555-0102",
                banking_details={"bank": "BOA", "account": "****5678"},
                role=CustomerRole.ORDER_STAFF,
            ),
            Customer(
                name="Carol Williams (Accountant)",
                address="789 Pine Rd, Springfield, IL",
                phone="+1-555-0103",
                banking_details={"bank": "Wells Fargo", "account": "****9012"},
                role=CustomerRole.ACCOUNTANT,
            ),
        ]
        session.add_all(customers)

        # Create sample products
        products = [
            Product(
                description="Wireless Bluetooth Headphones - Noise Cancelling",
                pricing={"base_price": 79.99, "currency": "USD"},
            ),
            Product(
                description="USB-C Charging Cable 6ft - Braided",
                pricing={"base_price": 12.99, "currency": "USD"},
            ),
            Product(
                description="Laptop Stand - Adjustable Aluminum",
                pricing={"base_price": 34.99, "currency": "USD"},
            ),
            Product(
                description="Mechanical Keyboard - RGB Backlit",
                pricing={"base_price": 89.99, "currency": "USD"},
            ),
            Product(
                description="Wireless Mouse - Ergonomic Design",
                pricing={"base_price": 24.99, "currency": "USD"},
            ),
            Product(
                description="27-inch 4K Monitor - IPS Panel",
                pricing={"base_price": 349.99, "currency": "USD"},
            ),
            Product(
                description="Webcam 1080p - Auto Focus",
                pricing={"base_price": 49.99, "currency": "USD"},
            ),
            Product(
                description="Desk Lamp - LED Touch Control",
                pricing={"base_price": 29.99, "currency": "USD"},
            ),
        ]
        session.add_all(products)

        await session.commit()
        print(f"Seeded {len(customers)} customers and {len(products)} products")


if __name__ == "__main__":
    asyncio.run(seed())
