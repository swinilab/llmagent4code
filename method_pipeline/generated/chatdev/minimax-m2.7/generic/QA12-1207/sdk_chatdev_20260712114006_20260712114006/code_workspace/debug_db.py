#!/usr/bin/env python3
"""Debug script to check database initialization"""
import tempfile
import os
import sqlite3

# Create temp db
fd, path = tempfile.mkstemp(suffix=".db")
os.close(fd)

print(f"Temp DB path: {path}")

# Simulate the flow
from app.adapters.persistence import DatabaseManager

# First test
manager1 = DatabaseManager(path)
print(f"manager1._initialized: {manager1._initialized}")
print(f"manager1._init_db_path: {manager1._init_db_path}")
manager1.init_schema()
print(f"After init_schema, manager1._initialized: {manager1._initialized}")

# Check what tables exist
conn1 = sqlite3.connect(path)
cursor1 = conn1.cursor()
cursor1.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables1 = cursor1.fetchall()
print(f"Tables after first init: {tables1}")
conn1.close()

# Second test (simulating what happens in second test)
manager2 = DatabaseManager(path)
print(f"\nmanager2._initialized: {manager2._initialized}")
print(f"manager2._init_db_path: {manager2._init_db_path}")
print(f"manager2.db_path: {manager2.db_path}")
manager2.init_schema()
print(f"After init_schema, manager2._initialized: {manager2._initialized}")

# Check what tables exist
conn2 = sqlite3.connect(path)
cursor2 = conn2.cursor()
cursor2.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables2 = cursor2.fetchall()
print(f"Tables after second init: {tables2}")
conn2.close()

# Try to write
try:
    conn3 = sqlite3.connect(path)
    conn3.execute("INSERT OR REPLACE INTO customers (id, name, email, phone, address_json, banking_details_json, role, order_history_json, is_active, created_at, updated_at) VALUES ('test', 'test', 'test@test.com', NULL, NULL, NULL, 'CUSTOMER', '[]', 1, '2024-01-01', '2024-01-01')")
    conn3.commit()
    print("Write succeeded!")
except Exception as e:
    print(f"Write failed: {e}")
finally:
    conn3.close()

# Cleanup
os.unlink(path)
