#!/usr/bin/env python3
"""Test script to verify the database connection pool fixes"""
import asyncio
import sys
import os
import pytest

# Add the parent directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.mark.asyncio
async def test_health_check():
    from app.db.connection_pool import health_check, init_db
    
    # Initialize the database first
    print("Initializing database...")
    await init_db()
    
    # Test health check
    print("Running health check...")
    result = await health_check()
    print(f"Health check result: {result}")
    
    return result


@pytest.mark.asyncio
async def test_db_fix():
    """Main test function with async decorator"""
    try:
        result = await test_health_check()
        assert result is True
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        raise
