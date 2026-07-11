"""
Seed data script — populates customers and products for development/testing.
Run: uv run python -m oms.seed
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from oms.infrastructure.database import AsyncSessionLocal
from oms.infrastructure.entities import CustomerModel, ProductModel
from oms.domain.enums import UserRole


SEED_CUSTOMER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SEED_PRODUCT_IDS = [
    uuid.UUID("00000000-0000-0000-0000-000000000010"),
    uuid.UUID("00000000-0000-0000-0000-000000000011"),
    uuid.UUID("00000000-0000-0000-0000-000000000012"),
]


def _utcnow() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(timezone.utc)


async def seed() -> None:
    """Insert seed data if tables are empty."""
    async with AsyncSessionLocal() as session:
        # Check if already seeded
        from sqlalchemy import select, func
        from oms.infrastructure.entities import Base

        result = await session.execute(select(func.count()).select_from(CustomerModel))
        count = result.scalar_one()
        if count > 0:
            print("Database already seeded, skipping.")
            return

        # Seed customer
        customer = CustomerModel(
            id=SEED_CUSTOMER_ID,
            name="John Doe",
            address="123 Main St, Springfield, USA",
            phone="+1-555-0100",
            banking_details="Bank of America, Account ****1234",
            role=UserRole.CUSTOMER,
            order_history=[],
        )
        session.add(customer)

        # Seed products
        products = [
            ProductModel(
                id=SEED_PRODUCT_IDS[0],
                description="High-performance laptop with 16GB RAM",
                base_price=Decimal("1299.99"),
                currency="USD",
                stock_available=100,
                last_modified=_utcnow(),
            ),
            ProductModel(
                id=SEED_PRODUCT_IDS[1],
                description="Wireless noise-cancelling headphones",
                base_price=Decimal("349.99"),
                currency="USD",
                stock_available=250,
                last_modified=_utcnow(),
            ),
            ProductModel(
                id=SEED_PRODUCT_IDS[2],
                description="Ergonomic mechanical keyboard",
                base_price=Decimal("159.99"),
                currency="USD",
                stock_available=500,
                last_modified=_utcnow(),
            ),
        ]
        for p in products:
            session.add(p)

        await session.commit()
        print("Seed data inserted successfully.")
        print(f"  Customer: {SEED_CUSTOMER_ID}")
        print(f"  Products: {[str(pid) for pid in SEED_PRODUCT_IDS]}")


if __name__ == "__main__":
    asyncio.run(seed())
