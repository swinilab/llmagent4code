#!/usr/bin/env python3
"""Debug customer service with session"""
import asyncio
import sys
sys.path.insert(0, '/home/swe/llmagent4code/method_pipeline_v2/generated/sdk_chatdev_20260725084518_20260725084518/code_workspace')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.db.tables import Base, CustomerTable
from app.repositories.customer_repository import CustomerRepository
from app.services.customer_service import CustomerService

async def debug():
    # Create engine and session
    engine = create_async_engine("sqlite+aiosqlite:///./oms.db", echo=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_factory() as session:
        try:
            repo = CustomerRepository(session)
            service = CustomerService(session)
            
            print("Creating customer via service...")
            customer = await service.create_customer(
                name="Test User",
                address="123 Main St",
                phone="+1234567890",
                account_number="123456789",
                bank_name="Test Bank",
                role="CUSTOMER"
            )
            print(f"Customer created: {customer}")
            await session.commit()
            print("Committed!")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(debug())
