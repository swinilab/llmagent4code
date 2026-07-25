#!/usr/bin/env python3
"""Debug customer creation with full traceback from server"""
import httpx
import asyncio
import sys
sys.path.insert(0, '/home/swe/llmagent4code/method_pipeline_v2/generated/sdk_chatdev_20260725084518_20260725084518/code_workspace')

from app.db.connection_pool import get_db, init_db, close_db
from app.services.customer_service import CustomerService
from app.models.customer import Customer, BankingDetails

async def debug_customer_direct():
    """Test customer creation directly without HTTP"""
    try:
        await init_db()
        async for session in get_db():
            service = CustomerService(session)
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
            break
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_db()

async def debug_customer_http():
    """Test customer creation via HTTP"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8000/api/v1/customers",
                json={
                    "name": "Test User",
                    "address": "123 Main St",
                    "phone": "+1234567890",
                    "accountNumber": "123456789",
                    "bankName": "Test Bank",
                    "role": "CUSTOMER"
                },
                timeout=10
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            if response.status_code == 500:
                print("Server error - check server logs for traceback")
        except httpx.HTTPError as e:
            print(f"HTTP Error: {e}")
            print(f"Response: {e.response.text if e.response else 'No response'}")
        except Exception as e:
            print(f"Exception: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("=== Direct DB test ===")
    asyncio.run(debug_customer_direct())
    print("\n=== HTTP test ===")
    asyncio.run(debug_customer_http())
