"""
Seed data script — populates the database with test customers and products.
"""
import asyncio
import sys

import httpx

BASE_URL = "http://localhost:8000"


async def seed():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        # Create customers
        customers = [
            {"name": "Alice Johnson", "address": "123 Main St, Springfield", "phone": "+1-555-0101", "banking_details": "ACC-001", "role": "CUSTOMER"},
            {"name": "Bob Smith", "address": "456 Oak Ave, Portland", "phone": "+1-555-0102", "banking_details": "ACC-002", "role": "CUSTOMER"},
            {"name": "Order Staff 1", "address": "789 Pine Rd, HQ", "phone": "+1-555-0201", "banking_details": "ACC-STAFF-01", "role": "ORDER_STAFF"},
            {"name": "Accountant 1", "address": "789 Pine Rd, HQ", "phone": "+1-555-0301", "banking_details": "ACC-ACCT-01", "role": "ACCOUNTANT"},
        ]
        for c in customers:
            resp = await client.post("/api/v1/customers", json=c)
            if resp.status_code == 201:
                print(f"Created customer: {c['name']} -> {resp.json()['id']}")

        # Create products
        products = [
            {"name": "Wireless Mouse", "description": "Ergonomic wireless mouse with USB-C charging", "base_price": 29.99, "stock_available": 500},
            {"name": "Mechanical Keyboard", "description": "RGB mechanical keyboard with Cherry MX switches", "base_price": 89.99, "stock_available": 200},
            {"name": "USB-C Hub", "description": "7-in-1 USB-C hub with HDMI, USB-A, SD card", "base_price": 34.99, "stock_available": 300},
            {"name": "27\" 4K Monitor", "description": "27-inch 4K UHD IPS monitor with HDR", "base_price": 399.99, "stock_available": 50},
            {"name": "Laptop Stand", "description": "Adjustable aluminum laptop stand", "base_price": 49.99, "stock_available": 150},
        ]
        for p in products:
            resp = await client.post("/api/v1/products", json=p)
            if resp.status_code == 201:
                print(f"Created product: {p['name']} -> {resp.json()['id']}")


if __name__ == "__main__":
    asyncio.run(seed())
