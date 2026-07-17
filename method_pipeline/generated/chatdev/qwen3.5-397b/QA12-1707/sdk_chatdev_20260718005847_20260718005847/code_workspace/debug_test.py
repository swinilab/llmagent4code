"""Debug test to find the actual error."""
import asyncio
from oms.config.database import db
from oms.models.customer import Customer, CustomerCreate
from oms.repositories.customer_repository import CustomerRepository

async def test():
    await db.initialize()
    
    async for session in db.get_session():
        try:
            # Test creating a customer directly
            customer_data = CustomerCreate(name="Test", email="test@test.com")
            repo = CustomerRepository(session)
            customer = await repo.create(customer_data)
            print(f"Customer created: {customer.id}, {customer.name}")
        except Exception as e:
            import traceback
            print(f"Error: {e}")
            traceback.print_exc()
        break

if __name__ == "__main__":
    asyncio.run(test())
