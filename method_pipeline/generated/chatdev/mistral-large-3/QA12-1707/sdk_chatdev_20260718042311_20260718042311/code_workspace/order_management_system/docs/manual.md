# Order Management System (OMS) - User Manual

## Table of Contents
- [1. Introduction](#1-introduction)
  - [1.1 Purpose](#11-purpose)
  - [1.2 Target Audience](#12-target-audience)
  - [1.3 System Overview](#13-system-overview)
- [2. Key Features](#2-key-features)
- [3. Architecture Overview](#3-architecture-overview)
  - [3.1 System Components](#31-system-components)
  - [3.2 Domain Model](#32-domain-model)
  - [3.3 User Workflows](#33-user-workflows)
- [4. Installation Guide](#4-installation-guide)
  - [4.1 Prerequisites](#41-prerequisites)
  - [4.2 Environment Setup](#42-environment-setup)
  - [4.3 Running the Application](#43-running-the-application)
  - [4.4 Infrastructure Setup](#44-infrastructure-setup)
- [5. API Documentation](#5-api-documentation)
  - [5.1 Base URL](#51-base-url)
  - [5.2 Endpoints](#52-endpoints)
    - [5.2.1 Customer APIs](#521-customer-apis)
    - [5.2.2 Order APIs](#522-order-apis)
    - [5.2.3 Invoice APIs](#523-invoice-apis)
    - [5.2.4 Payment APIs](#524-payment-apis)
    - [5.2.5 Product APIs](#525-product-apis)
- [6. Using the OMS](#6-using-the-oms)
  - [6.1 Placing an Order](#61-placing-an-order)
  - [6.2 Reviewing and Accepting an Order](#62-reviewing-and-accepting-an-order)
  - [6.3 Creating an Invoice](#63-creating-an-invoice)
  - [6.4 Processing a Payment](#64-processing-a-payment)
  - [6.5 Shipping an Order](#65-shipping-an-order)
  - [6.6 Closing an Order](#66-closing-an-order)
- [7. Observability and Verification](#7-observability-and-verification)
  - [7.1 Monitoring NFRs](#71-monitoring-nfrs)
  - [7.2 Logs and Metrics](#72-logs-and-metrics)
- [8. Troubleshooting](#8-troubleshooting)
  - [8.1 Common Issues](#81-common-issues)
  - [8.2 Support](#82-support)

---

## 1. Introduction

### 1.1 Purpose
The **Order Management System (OMS)** is a backend-only, production-grade system designed to manage the complete lifecycle of e-commerce orders. It supports three primary roles: **Customer**, **Order Staff**, and **Accountant**, and handles critical functions such as order placement, payment processing, invoicing, shipping, and order closure.

This manual provides comprehensive guidance on how to install, configure, and use the OMS, including detailed API documentation and user workflows.

### 1.2 Target Audience
This manual is intended for:
- **Developers**: Responsible for deploying, maintaining, and extending the OMS.
- **System Administrators**: Responsible for managing the infrastructure and ensuring system reliability.
- **End Users**: Including Customers, Order Staff, and Accountants who interact with the system via APIs.

### 1.3 System Overview
The OMS is built using **Python** and follows a **microservice-inspired modular architecture** with clear separation of concerns. It is designed to handle non-trivial traffic while ensuring **low latency**, **high concurrency**, and **fault tolerance**.

Key characteristics:
- **Backend-only**: Exposes RESTful APIs for all operations.
- **Role-based workflows**: Supports distinct workflows for Customers, Order Staff, and Accountants.
- **Production-grade**: Includes mechanisms for graceful degradation, fault detection, and state preservation.

---

## 2. Key Features

| Feature                          | Description                                                                                     |
|-----------------------------------|-------------------------------------------------------------------------------------------------|
| **Order Lifecycle Management**    | Supports the complete order workflow: placement, review, invoicing, payment, shipping, closure. |
| **Role-Based Access**             | Distinct APIs and workflows for Customers, Order Staff, and Accountants.                       |
| **Payment Processing**            | Handles payment creation, verification, and status updates.                                   |
| **Invoicing**                     | Generates invoices for accepted orders and tracks their status.                                |
| **Concurrency & Scalability**     | Optimized for high traffic with minimal latency and resource contention.                       |
| **Fault Tolerance**               | Detects failures, recovers automatically, and preserves state across restarts.                |
| **Observability**                 | Provides logs, metrics, and verification methods for monitoring NFRs.                          |

---

## 3. Architecture Overview

### 3.1 System Components

The OMS is structured into the following components:

1. **Controllers**: Handle HTTP requests, validate inputs, and map responses.
2. **Services**: Contain business logic, transaction boundaries, and orchestration.
3. **Repositories**: Manage data persistence and retrieval.
4. **Domain Models**: Define the core entities (Customer, Order, Product, Payment, Invoice).
5. **Infrastructure**: Includes configuration, database setup, and deployment scripts.
6. **Utilities**: Shared utilities for logging, error handling, and validation.

### 3.2 Domain Model

| Entity    | Attributes                                                                                     |
|------------|-------------------------------------------------------------------------------------------------|
| Customer  | `id`, `name`, `address`, `phone`, `banking_details`, `order_history`, `role`                   |
| Order     | `id`, `customer_ref`, `line_items`, `amounts`, `status`, `timestamps`, `invoice_ref`            |
| Product   | `id`, `description`, `pricing` (base + currency)                                                |
| Payment   | `id`, `order_ref`, `amount`, `timestamp`, `status`, `method`                                   |
| Invoice   | `id`, `order_ref`, `billing_info`, `amounts`, `issue_date`, `due_date`, `status`                |

**Order Status Lifecycle**:
`PLACED` → `REVIEWING` → `ACCEPTED` → `INVOICED` → `PAID` → `SHIPPED` → `CLOSED`

### 3.3 User Workflows

1. **Customer** places an order.
2. **Order Staff** reviews and accepts the order.
3. **Accountant** creates an invoice for the accepted order.
4. **Customer** pays the invoice.
5. **Accountant** verifies the payment.
6. **Order Staff** ships the paid order.
7. **Order Staff** closes the completed order.

---

## 4. Installation Guide

### 4.1 Prerequisites

Ensure the following software is installed on your system:
- **Python 3.10+**
- **UV** (Python package installer and resolver)
- **Docker** (for running PostgreSQL and Redis)
- **Git** (for version control)

### 4.2 Environment Setup

1. **Clone the Repository**
   ```bash
   git clone <repository_url>
   cd order_management_system
   ```

2. **Set Up Python Environment**
   ```bash
   uv venv --python 3.10
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate   # Windows
   ```

3. **Install Dependencies**
   ```bash
   uv add fastapi uvicorn sqlalchemy psycopg2-binary pydantic redis python-dotenv
   ```

4. **Set Up Environment Variables**
   Create a `.env` file in the root directory with the following content:
   ```env
   DATABASE_URL=postgresql://oms_user:oms_password@localhost:5432/oms_db
   REDIS_URL=redis://localhost:6379/0
   LOG_LEVEL=INFO
   ```

### 4.3 Running the Application

1. **Start Infrastructure Services**
   Use Docker to run PostgreSQL and Redis:
   ```bash
   docker-compose -f infrastructure/docker-compose.yml up -d
   ```

2. **Run Database Migrations**
   ```bash
   alembic upgrade head
   ```

3. **Start the OMS Backend**
   ```bash
   uvicorn app.main:app --reload
   ```

The application will be available at `http://localhost:8000`.

### 4.4 Infrastructure Setup

The `infrastructure` directory contains:
- `docker-compose.yml`: Defines PostgreSQL and Redis services.
- `init.sql`: Initializes the database schema and users.

To deploy the infrastructure:
```bash
cd infrastructure
docker-compose up -d
```

---

## 5. API Documentation

### 5.1 Base URL
All API endpoints are prefixed with:
```
http://localhost:8000/api/v1
```

### 5.2 Endpoints

#### 5.2.1 Customer APIs

| Method | Endpoint               | Description                          | Role       |
|--------|------------------------|--------------------------------------|------------|
| POST   | `/customers/`           | Create a new customer.               | Customer   |
| GET    | `/customers/{id}`       | Retrieve customer details.           | Customer   |
| PUT    | `/customers/{id}`       | Update customer details.             | Customer   |

#### 5.2.2 Order APIs

| Method | Endpoint               | Description                          | Role         |
|--------|------------------------|--------------------------------------|--------------|
| POST   | `/orders/`              | Place a new order.                   | Customer     |
| GET    | `/orders/{id}`          | Retrieve order details.              | Customer     |
| PUT    | `/orders/{id}/accept`   | Accept an order.                     | Order Staff  |
| PUT    | `/orders/{id}/ship`     | Ship an order.                       | Order Staff  |
| PUT    | `/orders/{id}/close`    | Close an order.                      | Order Staff  |

#### 5.2.3 Invoice APIs

| Method | Endpoint               | Description                          | Role         |
|--------|------------------------|--------------------------------------|--------------|
| POST   | `/invoices/`            | Create an invoice for an order.      | Accountant   |
| GET    | `/invoices/{id}`        | Retrieve invoice details.            | Accountant   |
| PUT    | `/invoices/{id}/verify` | Verify an invoice payment.           | Accountant   |

#### 5.2.4 Payment APIs

| Method | Endpoint               | Description                          | Role       |
|--------|------------------------|--------------------------------------|------------|
| POST   | `/payments/`            | Process a payment for an invoice.    | Customer   |
| GET    | `/payments/{id}`        | Retrieve payment details.            | Customer   |

#### 5.2.5 Product APIs

| Method | Endpoint               | Description                          | Role       |
|--------|------------------------|--------------------------------------|------------|
| GET    | `/products/`            | List all products.                   | Customer   |
| GET    | `/products/{id}`        | Retrieve product details.            | Customer   |

---

## 6. Using the OMS

### 6.1 Placing an Order

1. **Customer** sends a `POST` request to `/orders/` with the following payload:
   ```json
   {
     "customer_id": "cust_123",
     "line_items": [
       {
         "product_id": "prod_456",
         "quantity": 2,
         "price": 10.99
       }
     ]
   }
   ```

2. The system responds with the created order:
   ```json
   {
     "id": "order_789",
     "status": "PLACED",
     "customer_ref": "cust_123",
     "line_items": [
       {
         "product_id": "prod_456",
         "quantity": 2,
         "price": 10.99
       }
     ],
     "amounts": {
       "subtotal": 21.98,
       "tax": 2.20,
       "total": 24.18
     }
   }
   ```

### 6.2 Reviewing and Accepting an Order

1. **Order Staff** retrieves the order details using `GET /orders/{id}`.

2. **Order Staff** accepts the order by sending a `PUT` request to `/orders/{id}/accept`.

3. The system updates the order status to `ACCEPTED`.

### 6.3 Creating an Invoice

1. **Accountant** sends a `POST` request to `/invoices/` with the following payload:
   ```json
   {
     "order_id": "order_789",
     "billing_info": {
       "name": "John Doe",
       "address": "123 Main St"
     },
     "due_date": "2023-12-31"
   }
   ```

2. The system responds with the created invoice:
   ```json
   {
     "id": "inv_101",
     "order_ref": "order_789",
     "status": "ISSUED",
     "amounts": {
       "subtotal": 21.98,
       "tax": 2.20,
       "total": 24.18
     },
     "due_date": "2023-12-31"
   }
   ```

### 6.4 Processing a Payment

1. **Customer** sends a `POST` request to `/payments/` with the following payload:
   ```json
   {
     "invoice_id": "inv_101",
     "amount": 24.18,
     "method": "CREDIT_CARD"
   }
   ```

2. The system responds with the payment details:
   ```json
   {
     "id": "pay_202",
     "invoice_ref": "inv_101",
     "status": "PENDING",
     "amount": 24.18,
     "method": "CREDIT_CARD"
   }
   ```

3. **Accountant** verifies the payment by sending a `PUT` request to `/invoices/{id}/verify`.

### 6.5 Shipping an Order

1. **Order Staff** ships the order by sending a `PUT` request to `/orders/{id}/ship`.

2. The system updates the order status to `SHIPPED`.

### 6.6 Closing an Order

1. **Order Staff** closes the order by sending a `PUT` request to `/orders/{id}/close`.

2. The system updates the order status to `CLOSED`.

---

## 7. Observability and Verification

### 7.1 Monitoring NFRs

The following table describes how to verify each Non-Functional Requirement (NFR):

| NFR                          | Verification Method                                                                                     |
|-------------------------------|---------------------------------------------------------------------------------------------------------|
| **NFR 1.1 Response Time**     | Use load testing tools (e.g., Locust) to measure latency under load.                                   |
| **NFR 1.2 Concurrency**       | Monitor CPU, memory, and queue lengths using Prometheus and Grafana.                                   |
| **NFR 1.3 Queue Management**  | Simulate traffic spikes and observe system behavior using Redis queue metrics.                         |
| **NFR 2.1 Graceful Degradation** | Artificially induce resource contention and verify core checkout functionality remains available.      |
| **NFR 2.2 Fault Detection**   | Simulate component failures (e.g., database downtime) and verify automatic recovery.                   |
| **NFR 2.3 State Preservation** | Kill the application process and restart it to verify pending orders are restored from the database.   |

### 7.2 Logs and Metrics

- **Logs**: Stored in `logs/oms.log`. Configured to rotate daily.
- **Metrics**: Exposed via Prometheus at `http://localhost:8000/metrics`.

---

## 8. Troubleshooting

### 8.1 Common Issues

| Issue                          | Solution                                                                                               |
|---------------------------------|---------------------------------------------------------------------------------------------------------|
| **Database Connection Failed** | Verify PostgreSQL is running and the `DATABASE_URL` in `.env` is correct.                              |
| **Redis Connection Failed**    | Verify Redis is running and the `REDIS_URL` in `.env` is correct.                                      |
| **High Latency**               | Check system resources (CPU, memory) and optimize database queries.                                    |
| **Order Not Found**            | Verify the order ID exists in the database using `GET /orders/{id}`.                                   |

### 8.2 Support

For additional support, contact the development team at `support@chatdev.ai`.

---