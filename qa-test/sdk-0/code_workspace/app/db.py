import sqlite3
import os
from pathlib import Path

DB_PATH = Path('oms.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

async def init_db():
    # Create tables if not exist – definitions aligned with ORM models
    conn = get_connection()
    cur = conn.cursor()
    # Customers table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS customers (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        address TEXT NOT NULL,
        phone TEXT NOT NULL,
        banking_details TEXT NOT NULL, -- JSON {accountNumber, bankName}
        role TEXT NOT NULL,
        order_history TEXT -- JSON array of UUID strings
    )
    ''')
    # Products table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        description TEXT NOT NULL,
        price_amount TEXT NOT NULL,
        price_currency TEXT NOT NULL
    )
    ''')
    # Orders table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        line_items TEXT NOT NULL, -- JSON list of line items
        total_amount TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        invoice_id TEXT
    )
    ''')
    # Payments table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id TEXT PRIMARY KEY,
        order_id TEXT NOT NULL,
        amount TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        status TEXT NOT NULL,
        method TEXT NOT NULL
    )
    ''')
    # Invoices table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS invoices (
        id TEXT PRIMARY KEY,
        order_id TEXT NOT NULL,
        billing_info TEXT NOT NULL, -- JSON {name, address}
        total_amount TEXT NOT NULL,
        issue_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        status TEXT NOT NULL
    )
    ''')
    conn.commit()
    conn.close()

async def close_db():
    # No persistent connection to close in this simple implementation
    pass
