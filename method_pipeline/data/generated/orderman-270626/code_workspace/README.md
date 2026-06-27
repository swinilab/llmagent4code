# Order Management System

A comprehensive full-stack web application for managing the complete order workflow from customer orders to payment processing and shipping.

## Features

- **Multi-role Support**: Customers, Order Staff, and Accountants
- **Complete Order Lifecycle**: From order placement to completion
- **RESTful API**: Module-based Domain-Driven Design
- **Modern Frontend**: Clean, responsive UI with vanilla JavaScript
- **SQLite Database**: Locally deployable with async support

## Order Workflow

1. **Customer** places an order
2. **Order Staff** reviews and accepts the order
3. **Accountant** creates an invoice for the accepted order
4. **Customer** makes payment on the issued invoice
5. **Accountant** tracks if order is paid
6. **Order Staff** ships the order once paid
7. **Order Staff** closes the completed order

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy (async), SQLite
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Package Manager**: uv

## Installation & Setup

### Prerequisites

- Python 3.12 or higher
- uv package manager

### Installation Steps

1. **Clone or navigate to the project directory**

2. **Initialize Python environment**
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   uv sync
   ```

4. **Run the application**
   ```bash
   uv run python main.py
   ```

5. **Access the application**
   - Frontend: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## Project Structure

```
.
├── main.py                 # Application entry point
├── server.py               # FastAPI server configuration
├── pyproject.toml          # Project dependencies
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

## API Endpoints

### Customers
- `GET /api/customers` - List all customers
- `GET /api/customers/{id}` - Get customer by ID
- `GET /api/customers/email/{email}` - Get customer by email
- `POST /api/customers` - Create customer
- `PUT /api/customers/{id}` - Update customer
- `DELETE /api/customers/{id}` - Delete customer

### Products
- `GET /api/products` - List all products
- `GET /api/products/{id}` - Get product by ID
- `GET /api/products/sku/{sku}` - Get product by SKU
- `POST /api/products` - Create product
- `PUT /api/products/{id}` - Update product
- `PATCH /api/products/{id}/stock` - Adjust stock
- `DELETE /api/products/{id}` - Delete product

### Orders
- `GET /api/orders` - List all orders
- `GET /api/orders/{id}` - Get order by ID
- `POST /api/orders` - Create order (Customer)
- `POST /api/orders/{id}/accept` - Accept order (Order Staff)
- `POST /api/orders/{id}/ship` - Ship order (Order Staff)
- `POST /api/orders/{id}/complete` - Complete order (Order Staff)
- `POST /api/orders/{id}/cancel` - Cancel order
- `PUT /api/orders/{id}` - Update order
- `DELETE /api/orders/{id}` - Delete order

### Invoices
- `GET /api/invoices` - List all invoices
- `GET /api/invoices/{id}` - Get invoice by ID
- `GET /api/invoices/order/{order_id}` - Get invoice by order
- `POST /api/invoices` - Create invoice (Accountant)
- `POST /api/invoices/{id}/pay` - Mark invoice as paid
- `POST /api/invoices/{id}/cancel` - Cancel invoice
- `POST /api/invoices/check-overdue` - Check overdue invoices
- `PUT /api/invoices/{id}` - Update invoice
- `DELETE /api/invoices/{id}` - Delete invoice

### Payments
- `GET /api/payments` - List all payments
- `GET /api/payments/{id}` - Get payment by ID
- `POST /api/payments` - Create payment (Customer)
- `POST /api/payments/{id}/refund` - Refund payment
- `POST /api/payments/{id}/fail` - Mark payment as failed
- `PUT /api/payments/{id}` - Update payment
- `DELETE /api/payments/{id}` - Delete payment

## Configuration

Environment variables (optional):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./order_management.db` | Database connection string |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `RELOAD` | `false` | Enable auto-reload |
| `DB_POOL_SIZE` | `10` | Database connection pool size |
| `FEATURE_ANALYTICS` | `true` | Enable analytics |
| `FEATURE_RECOMMENDATIONS` | `true` | Enable recommendations |
| `FEATURE_HEAVY_LOGGING` | `false` | Enable detailed logging |

## Non-Functional Requirements

### Performance
- **NFR 1.1**: Optimized API response times for core operations
- **NFR 1.2**: Efficient resource utilization with async processing
- **NFR 1.3**: Graceful handling of traffic spikes

### Modifiability
- **NFR 2.1**: Business rules isolated in service layer
- **NFR 2.2**: Stable API contracts for frontend independence
- **NFR 2.3**: Runtime configuration via environment variables

### Reliability
- **NFR 3.1**: Graceful degradation of non-essential features
- **NFR 3.2**: Automatic fault detection and recovery
- **NFR 3.3**: State preservation on restart

## Sample Data

On first run, the system seeds:
- 4 sample users (2 customers, 1 order staff, 1 accountant)
- 5 sample products

## License

© 2024 Order Management System. All rights reserved.
