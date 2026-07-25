#!/usr/bin/env python3
"""Debug customer creation with full traceback from server"""
import httpx
import asyncio

async def debug_customer():
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
    asyncio.run(debug_customer())
