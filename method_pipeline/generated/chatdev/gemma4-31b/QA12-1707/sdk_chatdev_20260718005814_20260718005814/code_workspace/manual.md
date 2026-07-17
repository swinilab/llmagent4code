# 📦 Order Management System (OMS) - User & Operations Manual

## 1. Introduction
The OMS is a production-grade backend system designed to manage the end-to-end lifecycle of customer orders. It orchestrates the workflow between Customers, Order Staff, and Accountants to ensure a seamless transition from product selection to order closure.

### Core Workflow
`Customer Order` $\rightarrow$ `Staff Review` $\rightarrow$ `Invoice Generation` $\rightarrow$ `Payment` $\rightarrow$ `Payment Verification` $\rightarrow$ `Shipping` $\rightarrow$ `Closure`.

---

## 2. System Architecture & NFR Implementation
This system is engineered for high availability and resilience. Below is how the Non-Functional Requirements (NFRs) are handled:

### NFR Traceability Matrix
| NFR ID | Requirement | Architectural Mechanism | Component | Verification Method |
| :--- | :--- | :--- | :--- | :--- |
| **1.1** | Response Time | Asynchronous I/O & Connection Pooling | FastAPI / SQLAlchemy | Measure API latency via `curl` or Postman under load. |
| **1.2** | Concurrency | Asyncio Event Loop & Worker Scaling | Uvicorn / Gunicorn | Monitor CPU/RAM usage during concurrent request bursts. |
| **1.3** | Queue Management | Distributed Task Queue (Celery/Redis) | Task Worker | Inject 10k requests; observe queue growth without crash. |
| **2.1** | Graceful Degradation | Circuit Breaker & Feature Toggles | Middleware | Simulate DB latency; verify "Search" fails while "Checkout" stays up. |
| **2.2** | Fault Recovery | Automatic Retry Logic & Health Checks | Service Layer | Kill a worker process; observe automatic restart/reconnect. |
| **2.3** | State Preservation | WAL (Write-Ahead Logging) & Persistent DB | PostgreSQL | Force crash during order process; verify state on reboot. |

### Architectural Decision Records (ADR)
- **Decision:** Use **FastAPI** with **SQLAlchemy (Async)**.
    - *Context:* NFR 1.1, 1.2.
    - *Alternatives:* Flask (Sync, slower), Django (Heavier overhead).
    - *Consequences:* Requires `async/await` discipline throughout the codebase.
- **Decision:** Use **Redis** for distributed state and queuing.
    - *Context:* NFR 1.3, 2.3.
    - *Alternatives:* RabbitMQ (Complex setup), In-memory lists (Lossy).
    - *Consequences:* Adds a network dependency; requires Redis container.
- **Decision:** **State-Machine Based Order Status**.
    - *Context:* Domain integrity.
    - *Alternatives:* Simple string updates (Prone to illegal transitions).
    - *Consequences:* Strict validation on every status change.

---

## 3. Installation & Deployment

### Prerequisites
- Python 3.10+
- Docker & Docker Compose

### Local Setup
1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd oms-backend
   ```

2. **Launch Infrastructure (Database & Cache):**
   ```bash
   docker-compose up -d
   ```

3. **Environment Setup:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Run the Application:**
   ```bash
   uvicorn main:app --reload --port 8000
   ```

---

## 4. User Guide: Playing with the System

The system is backend-only. Use the built-in **Swagger UI** for interaction:
👉 `http://localhost:8000/docs`

### Role-Based Walkthrough

#### 👤 As a Customer
1. **Browse Products:** `GET /products`
2. **Place Order:** `POST /orders` (Provide product IDs and shipping address).
   - *Status: PENDING*
3. **Pay Invoice:** `POST /payments` (Provide Invoice ID and payment details).
   - *Status: PAID*

#### 🛠️ As Order Staff
1. **Review Orders:** `GET /orders?status=PENDING`
2. **Accept Order:** `PATCH /orders/{id}/status` $\rightarrow$ `ACCEPTED`
3. **Ship Order:** `PATCH /orders/{id}/status` $\rightarrow$ `SHIPPED` (Only after payment is verified).
4. **Close Order:** `PATCH /orders/{id}/status` $\rightarrow$ `CLOSED`

#### 💰 As an Accountant
1. **Generate Invoice:** `POST /invoices` (Link to an `ACCEPTED` order).
2. **Verify Payment:** `PATCH /payments/{id}/status` $\rightarrow$ `VERIFIED`

---

## 5. Verification Checklist for Reviewers

To verify the system meets the production-grade requirements:

- [ ] **Latency Test:** Run `ab -n 1000 -c 10 http://localhost:8000/products` to verify NFR 1.1.
- [ ] **Crash Test:** While a payment is processing, restart the server. Verify the order does not disappear (NFR 2.3).
- [ ] **Workflow Test:** Attempt to "Ship" an order that hasn't been "Paid". The system must return a `400 Bad Request` (Domain Validation).
- [ ] **Load Test:** Flood the `/orders` endpoint; verify that the Redis queue handles the spike without dropping requests (NFR 1.3).
