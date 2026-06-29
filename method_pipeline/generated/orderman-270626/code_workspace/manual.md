# Order Management System - User Manual

## Table of Contents

1. [Introduction](#introduction)
2. [System Overview](#system-overview)
3. [Installation & Setup](#installation--setup)
4. [Running the Application](#running-the-application)
5. [User Roles & Permissions](#user-roles--permissions)
6. [Complete Workflow Guide](#complete-workflow-guide)
7. [Module Reference](#module-reference)
8. [API Reference](#api-reference)
9. [Configuration](#configuration)
10. [Troubleshooting](#troubleshooting)

---

## Introduction

Welcome to the **Order Management System**, a comprehensive full-stack web application designed to handle the complete order workflow from customer orders to payment processing and shipping. This system is built using modern web technologies and follows RESTful, module-based Domain-Driven Design principles.

### Key Features

- **Multi-role Support**: Three distinct user roles (Customers, Order Staff, Accountants)
- **Complete Order Lifecycle**: Manage orders from placement through completion
- **RESTful API**: Clean, well-documented API endpoints
- **Modern Frontend**: Responsive, intuitive user interface
- **SQLite Database**: Easy local deployment with async support
- **Real-time Status Tracking**: Monitor order, invoice, and payment statuses

---

## System Overview

### Architecture

The system follows a three-layer architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (HTML/CSS/JS)                  │
│  - Dashboard, Forms, Lists for all entities                 │
└─────────────────────────────────────────────────────────────┘
                            ↕ REST API
┌─────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI/Python)                │
│  - Routes → Controllers → Services → Database               │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                   Database (SQLite with SQLAlchemy)          │
│  - Customers, Products, Orders, Invoices, Payments          │
└─────────────────────────────────────────────────────────────┘
```

### Core Entities

| Entity | Description |
|--------|-------------|
| **Customer** | User accounts with contact info, banking details, and order history |
| **Product** | Items available for purchase with pricing and stock tracking |
| **Order** | Customer orders containing items, status tracking, and shipping info |
| **Invoice** | Billing documents linked to orders with due dates and amounts |
| **Payment** | Transaction records for invoice payments |

---

## Installation & Setup

### Prerequisites

Before installing the Order Management System, ensure you have the following:

- **Python 3.12 or higher**
- **uv package manager** (recommended for dependency management)

### Step 1: Verify Python Installation

Open a terminal and check your Python version:

```bash
python --version
```

You should see Python 3.12 or higher. If not, download and install from [python.org](https://www.python.org/downloads/).

### Step 2: Install uv Package Manager

If you don't have uv installed:

```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Step 3: Navigate to Project Directory

```bash
cd /path/to/order-management-system
```

### Step 4: Initialize Python Environment

Create a virtual environment:

```bash
uv venv
```

Activate the virtual environment:

```bash
# On macOS/Linux
source .venv/bin/activate

# On Windows
.venv\Scripts\activate
```

### Step 5: Install Dependencies

Install all required packages:

```bash
uv sync
```

This will install:
- `fastapi` - Web framework for the API
- `uvicorn` - ASGI server
- `sqlalchemy` - Database ORM
- `aiosqlite` - Async SQLite support
- `pydantic` - Data validation

### Step 6: Verify Installation

Check that all dependencies are installed:

```bash
uv pip list
```

---

## Running the Application

### Start the Server

Run the application using:

```bash
uv run python main.py
```

You should see output similar to:

```
INFO - Starting Order Management System...
INFO - Database initialized successfully
INFO - Initial data seeded successfully
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Access the Application

Open your web browser and navigate to:

| Resource | URL |
|----------|-----|
| **Frontend UI** | http://localhost:8000 |
| **API Documentation** | http://localhost:8000/docs |
| **Health Check** | http://localhost:8000/health |

### Stop the Server

Press `Ctrl+C` in the terminal to stop the server.

---

## User Roles & Permissions

The system supports three user roles, each with specific permissions:

### Customer

**Responsibilities:**
- Browse products
- Place new orders
- Make payments on invoices
- View order history

**Available Actions:**
- Create orders
- View own orders
- Make payments
- Update profile information

### Order Staff

**Responsibilities:**
- Review incoming orders
- Accept or reject orders
- Ship orders once paid
- Close completed orders

**Available Actions:**
- Accept pending orders
- Ship paid orders
- Complete shipped orders
- Cancel orders (before shipping)

### Accountant

**Responsibilities:**
- Create invoices for accepted orders
- Track payment status
- Monitor overdue invoices
- Manage payment records

**Available Actions:**
- Create invoices
- Mark invoices as paid
- View payment records
- Check overdue invoices

> **Note:** The current implementation does not require login. Users select their role implicitly by using the appropriate features.

---

## Complete Workflow Guide

This section walks you through the complete order lifecycle from start to finish.

### Step 1: Customer Places an Order

**Actor:** Customer

1. Navigate to the **Products** view
2. Review available products and prices
3. Click the **"Place Order"** button in the Orders view
4. Fill in the order form:
   - Select customer from dropdown
   - Enter shipping address
   - Add order items (select product, quantity, price)
   - Add optional notes
5. Click **"Place Order"** to submit

**Result:** Order is created with status `PENDING`

### Step 2: Order Staff Reviews and Accepts Order

**Actor:** Order Staff

1. Navigate to the **Orders** view
2. Filter by status `PENDING` to see new orders
3. Review order details (items, customer, shipping address)
4. Click **"Accept Order"** button

**Result:** Order status changes to `ACCEPTED`

### Step 3: Accountant Creates Invoice

**Actor:** Accountant

1. Navigate to the **Invoices** view
2. Click **"Create Invoice"** button
3. Fill in the invoice form:
   - Select the accepted order
   - Customer is auto-filled
   - Amount is auto-filled from order total
   - Set due date (default: 30 days)
   - Enter billing address
4. Click **"Create Invoice"**

**Result:** Invoice is created with status `ISSUED`, Order status changes to `INVOICED`

### Step 4: Customer Makes Payment

**Actor:** Customer

1. Navigate to the **Payments** view
2. Click **"Make Payment"** button
3. Fill in the payment form:
   - Select the invoice to pay
   - Customer is auto-filled
   - Amount is auto-filled from invoice
   - Select payment method (Credit Card, Bank Transfer, etc.)
   - Optionally enter transaction ID
4. Click **"Make Payment"**

**Result:** Payment is created with status `COMPLETED`, Invoice status changes to `PAID`, Order status changes to `PAID`

### Step 5: Accountant Tracks Payment

**Actor:** Accountant

1. Navigate to the **Invoices** view
2. Filter by status `PAID` to see paid invoices
3. Verify payment has been received
4. (Optional) Navigate to **Payments** view to see payment details

**Result:** Payment is confirmed and tracked

### Step 6: Order Staff Ships Order

**Actor:** Order Staff

1. Navigate to the **Orders** view
2. Filter by status `PAID` to see orders ready for shipping
3. Click **"Ship Order"** button

**Result:** Order status changes to `SHIPPED`

### Step 7: Order Staff Completes Order

**Actor:** Order Staff

1. Navigate to the **Orders** view
2. Filter by status `SHIPPED` to see shipped orders
3. Click **"Complete Order"** button

**Result:** Order status changes to `COMPLETED`

### Workflow Diagram

```
┌─────────────┐
│   PENDING   │ ◄── Customer places order
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   ACCEPTED  │ ◄── Order Staff accepts
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   INVOICED  │ ◄── Accountant creates invoice
└──────┬──────┘
       │
       ▼
┌─────────────┐
│     PAID    │ ◄── Customer makes payment
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    SHIPPED  │ ◄── Order Staff ships
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  COMPLETED  │ ◄── Order Staff completes
└─────────────┘
```

---

## Module Reference

### Dashboard

**Purpose:** Overview of system statistics and workflow guide

**Features:**
- Real-time counts of customers, products, orders, invoices, and payments
- Visual workflow guide showing the order lifecycle
- Quick navigation to all modules

**Access:** Click "Dashboard" in the navigation bar

### Customers Module

**Purpose:** Manage customer accounts

**Features:**
- **Overview:** View all customers in a list
- **Add Customer:** Create new customer accounts
- **View Details:** See customer information and order history
- **Edit:** Update customer details
- **Delete:** Remove customer accounts

**Customer Information:**
- Name
- Email (unique identifier)
- Phone
- Address
- Banking details (optional)
- Role (Customer, Order Staff, Accountant)

### Products Module

**Purpose:** Manage product catalog

**Features:**
- **Overview:** View all products in a list
- **Add Product:** Create new products
- **View Details:** See product information
- **Edit:** Update product details
- **Adjust Stock:** Increase or decrease inventory
- **Delete:** Remove products

**Product Information:**
- Name
- Description
- SKU (unique identifier)
- Price
- Stock quantity

### Orders Module

**Purpose:** Manage customer orders through the complete lifecycle

**Features:**
- **Overview:** View all orders with status filtering
- **Place Order:** Create new orders (Customer action)
- **Accept Order:** Accept pending orders (Order Staff action)
- **Ship Order:** Ship paid orders (Order Staff action)
- **Complete Order:** Complete shipped orders (Order Staff action)
- **Cancel Order:** Cancel orders before completion
- **View Details:** See order items and history

**Order Statuses:**
| Status | Description | Next Action |
|--------|-------------|-------------|
| PENDING | Order placed, awaiting review | Accept or Cancel |
| ACCEPTED | Order approved by staff | Create Invoice |
| INVOICED | Invoice created | Customer Payment |
| PAID | Payment received | Ship Order |
| SHIPPED | Order shipped | Complete Order |
| COMPLETED | Order fulfilled | None (terminal) |
| CANCELLED | Order cancelled | None (terminal) |

### Invoices Module

**Purpose:** Manage billing and invoicing

**Features:**
- **Overview:** View all invoices with status filtering
- **Create Invoice:** Generate invoices for accepted orders (Accountant action)
- **Mark as Paid:** Record payment receipt
- **Cancel Invoice:** Cancel issued invoices
- **Check Overdue:** Identify overdue invoices
- **View Details:** See invoice information

**Invoice Statuses:**
| Status | Description |
|--------|-------------|
| DRAFT | Invoice being prepared |
| ISSUED | Invoice sent to customer |
| PAID | Payment received |
| OVERDUE | Payment past due date |
| CANCELLED | Invoice cancelled |

### Payments Module

**Purpose:** Manage payment transactions

**Features:**
- **Overview:** View all payments with status filtering
- **Make Payment:** Process customer payments
- **Refund:** Issue refunds for completed payments
- **Mark as Failed:** Record failed payments
- **View Details:** See payment information

**Payment Statuses:**
| Status | Description |
|--------|-------------|
| PENDING | Payment initiated |
| PROCESSING | Payment being processed |
| COMPLETED | Payment successful |
| FAILED | Payment failed |
| REFUNDED | Payment refunded |

---

## API Reference

The system provides a RESTful API for programmatic access. Full interactive documentation is available at http://localhost:8000/docs

### Base URL

```
http://localhost:8000/api
```

### Customers API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/customers` | List all customers |
| GET | `/customers/{id}` | Get customer by ID |
| GET | `/customers/email/{email}` | Get customer by email |
| POST | `/customers` | Create customer |
| PUT | `/customers/{id}` | Update customer |
| DELETE | `/customers/{id}` | Delete customer |

**Example - Create Customer:**
```bash
curl -X POST http://localhost:8000/api/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "555-0100",
    "address": "123 Main St, City, State 12345",
    "banking_details": "Account: 12345678",
    "role": "customer"
  }'
```

### Products API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/products` | List all products |
| GET | `/products/{id}` | Get product by ID |
| GET | `/products/sku/{sku}` | Get product by SKU |
| POST | `/products` | Create product |
| PUT | `/products/{id}` | Update product |
| PATCH | `/products/{id}/stock` | Adjust stock |
| DELETE | `/products/{id}` | Delete product |

**Example - Create Product:**
```bash
curl -X POST http://localhost:8000/api/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Widget Pro",
    "description": "Professional grade widget",
    "price": 29.99,
    "sku": "WGT-PRO-001",
    "stock_quantity": 100
  }'
```

### Orders API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/orders` | List all orders |
| GET | `/orders/{id}` | Get order by ID |
| POST | `/orders` | Create order |
| POST | `/orders/{id}/accept` | Accept order |
| POST | `/orders/{id}/ship` | Ship order |
| POST | `/orders/{id}/complete` | Complete order |
| POST | `/orders/{id}/cancel` | Cancel order |
| PUT | `/orders/{id}` | Update order |
| DELETE | `/orders/{id}` | Delete order |

**Example - Create Order:**
```bash
curl -X POST http://localhost:8000/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "items": [
      {
        "product_id": 1,
        "product_name": "Widget Pro",
        "quantity": 2,
        "unit_price": 29.99,
        "subtotal": 59.98
      }
    ],
    "total_amount": 59.98,
    "shipping_address": "123 Main St, City, State 12345",
    "notes": "Please deliver before 5 PM"
  }'
```

### Invoices API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/invoices` | List all invoices |
| GET | `/invoices/{id}` | Get invoice by ID |
| GET | `/invoices/order/{order_id}` | Get invoice by order |
| POST | `/invoices` | Create invoice |
| POST | `/invoices/{id}/pay` | Mark as paid |
| POST | `/invoices/{id}/cancel` | Cancel invoice |
| POST | `/invoices/check-overdue` | Check overdue |
| PUT | `/invoices/{id}` | Update invoice |
| DELETE | `/invoices/{id}` | Delete invoice |

**Example - Create Invoice:**
```bash
curl -X POST http://localhost:8000/api/invoices \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": 1,
    "customer_id": 1,
    "amount": 59.98,
    "due_date": "2024-02-15T00:00:00",
    "billing_address": "123 Main St, City, State 12345"
  }'
```

### Payments API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/payments` | List all payments |
| GET | `/payments/{id}` | Get payment by ID |
| POST | `/payments` | Create payment |
| POST | `/payments/{id}/refund` | Refund payment |
| POST | `/payments/{id}/fail` | Mark as failed |
| PUT | `/payments/{id}` | Update payment |
| DELETE | `/payments/{id}` | Delete payment |

**Example - Create Payment:**
```bash
curl -X POST http://localhost:8000/api/payments \
  -H "Content-Type: application/json" \
  -d '{
    "invoice_id": 1,
    "customer_id": 1,
    "amount": 59.98,
    "payment_method": "credit_card",
    "transaction_id": "TXN-123456"
  }'
```

### Response Format

All API responses follow a consistent format:

**Success Response:**
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation successful"
}
```

**Error Response:**
```json
{
  "success": false,
  "message": "Error description",
  "detail": "Additional details"
}
```

**List Response:**
```json
{
  "success": true,
  "total": 100,
  "skip": 0,
  "limit": 10,
  "orders": [ ... ]
}
```

---

## Configuration

### Environment Variables

The system supports configuration via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./order_management.db` | Database connection string |
| `HOST` | `0.0.0.0` | Server host address |
| `PORT` | `8000` | Server port number |
| `RELOAD` | `false` | Enable auto-reload during development |
| `DB_POOL_SIZE` | `10` | Database connection pool size |
| `DB_MAX_OVERFLOW` | `20` | Maximum overflow connections |
| `DB_POOL_TIMEOUT` | `30` | Connection pool timeout (seconds) |
| `DB_POOL_RECYCLE` | `1800` | Connection recycle time (seconds) |
| `FEATURE_ANALYTICS` | `true` | Enable analytics features |
| `FEATURE_RECOMMENDATIONS` | `true` | Enable recommendation features |
| `FEATURE_HEAVY_LOGGING` | `false` | Enable detailed logging |
| `CACHE_EXPIRATION` | `300` | Cache expiration time (seconds) |

### Setting Environment Variables

**On macOS/Linux:**
```bash
export PORT=8080
export DB_POOL_SIZE=20
export FEATURE_HEAVY_LOGGING=true
uv run python main.py
```

**On Windows (Command Prompt):**
```cmd
set PORT=8080
set DB_POOL_SIZE=20
uv run python main.py
```

**On Windows (PowerShell):**
```powershell
$env:PORT=8080
$env:DB_POOL_SIZE=20
uv run python main.py
```

### Database Configuration

The system uses SQLite for local deployment. The database file `order_management.db` is created automatically on first run.

**To reset the database:**
1. Stop the server
2. Delete the `order_management.db` file
3. Restart the server

The database will be recreated with fresh seed data.

---

## Troubleshooting

### Common Issues

#### Server Won't Start

**Symptom:** Error when running `uv run python main.py`

**Solutions:**
1. Verify Python version: `python --version` (must be 3.12+)
2. Reinstall dependencies: `uv sync`
3. Check if port 8000 is in use: `lsof -i :8000` (macOS/Linux) or `netstat -ano | findstr :8000` (Windows)
4. Change port: `export PORT=8080` then restart

#### Database Errors

**Symptom:** Database connection or initialization errors

**Solutions:**
1. Check file permissions on the workspace directory
2. Delete `order_management.db` and restart
3. Verify `DATABASE_URL` environment variable

#### Frontend Not Loading

**Symptom:** Blank page or loading errors in browser

**Solutions:**
1. Verify server is running (check terminal output)
2. Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
3. Check browser console for JavaScript errors (F12)
4. Verify frontend files exist in the `frontend/` directory

#### API Requests Failing

**Symptom:** 404 or 500 errors from API calls

**Solutions:**
1. Check API endpoint URLs (case-sensitive)
2. Verify request body format matches API documentation
3. Check server logs for error details
4. Use API documentation at http://localhost:8000/docs to test endpoints

#### Orders Not Showing in Invoice Dropdown

**Symptom:** No orders appear when creating an invoice

**Solution:** Only orders with status `ACCEPTED` can be invoiced. Ensure the order has been accepted by Order Staff first.

#### Payments Not Processing

**Symptom:** Invoice not appearing in payment dropdown

**Solution:** Only invoices with status `ISSUED` or `OVERDUE` can be paid. Ensure the invoice has been created and issued.

### Getting Help

If you encounter issues not covered in this manual:

1. **Check Server Logs:** Review terminal output for error messages
2. **API Documentation:** Visit http://localhost:8000/docs for interactive API testing
3. **Browser Console:** Press F12 to view JavaScript errors
4. **Database Inspection:** Use SQLite tools to examine `order_management.db`

### Performance Tips

- **Large Datasets:** Use pagination parameters (`skip`, `limit`) for large data sets
- **Concurrent Users:** Increase `DB_POOL_SIZE` for high concurrency
- **Slow Queries:** Enable `FEATURE_HEAVY_LOGGING` to debug slow operations
- **Memory Usage:** Monitor system resources; the system is optimized for the available 98GB RAM

---

## Appendix

### Sample Data

On first run, the system seeds the following sample data:

**Users:**
- 2 Customer accounts
- 1 Order Staff account
- 1 Accountant account

**Products:**
- 5 sample products with varying prices

### File Structure

```
.
├── main.py                 # Application entry point
├── server.py               # FastAPI server configuration
├── pyproject.toml          # Project dependencies
├── uv.lock                 # Dependency lock file
├── order_management.db     # SQLite database (created on first run)
├── database/
│   ├── __init__.py
│   ├── config.py           # Database configuration
│   └── models.py           # SQLAlchemy ORM models
├── shared/
│   ├── __init__.py
│   └── models.py           # Pydantic domain models
├── services/
│   ├── __init__.py
│   ├── customer_service.py
│   ├── product_service.py
│   ├── order_service.py
│   ├── invoice_service.py
│   └── payment_service.py
├── controllers/
│   ├── __init__.py
│   ├── customer_controller.py
│   ├── product_controller.py
│   ├── order_controller.py
│   ├── invoice_controller.py
│   └── payment_controller.py
├── routes/
│   ├── __init__.py
│   ├── customer_routes.py
│   ├── product_routes.py
│   ├── order_routes.py
│   ├── invoice_routes.py
│   └── payment_routes.py
└── frontend/
    ├── index.html
    ├── css/
    │   └── styles.css
    └── js/
        ├── api.js
        ├── app.js
        ├── customers.js
        ├── products.js
        ├── orders.js
        ├── invoices.js
        └── payments.js
```

### Version Information

- **System Version:** 1.0.0
- **Python Requirement:** 3.12+
- **Database:** SQLite with async support
- **API Version:** v1

---

© 2024 Order Management System. All rights reserved.
