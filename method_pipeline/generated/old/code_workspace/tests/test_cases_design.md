# Test Cases Specification: Order Management System (OMS)

This document defines the complete test case specifications for the Order Management System (OMS) across all architectural layers.

---

## 1. Customer Module Test Cases

### 1.1 Customer Service (`CustomerService`)

| Test Case ID | Target Method | Scenario Description | Inputs / Prerequisites | Expected Outcome / Assertions |
| :--- | :--- | :--- | :--- | :--- |
| **TC-SRV-CUST-01** | `create_customer` | Happy Path: Successfully create a new active customer with complete valid profile. | `name="Alice Smith"`, `email="alice@example.com"`, `phone="+12345678"`, `address="123 Main St"` | Returns `CustomerResponse` with populated `id`, default `is_active=True`, and current timestamps. |
| **TC-SRV-CUST-02** | `create_customer` | Duplicate Email: Attempt to create a customer with an email address that is already registered. | Email `"alice@example.com"` exists in repository. | Raises `ValueError` ("Customer with email alice@example.com already exists"). Database transaction rolls back. |
| **TC-SRV-CUST-03** | `create_customer` | Boundary Case: Create customer with minimum length name. | `name="A"`, `email="a@example.com"`. | Successfully creates customer. |
| **TC-SRV-CUST-04** | `create_customer` | Null Optional Fields: Create customer providing only name and email. | `name="Bob"`, `email="bob@example.com"`, other fields `None`. | Successfully creates customer; optional columns initialized as null. |
| **TC-SRV-CUST-05** | `get_customer` | Fetch Existing Customer: Retrieve a customer profile by its ID. | Valid customer exists in DB with `id=1`. | Returns matching `CustomerResponse` metadata. |
| **TC-SRV-CUST-06** | `get_customer` | Fetch Non-Existent Customer: Retrieve a customer by a random/unused ID. | No customer exists in DB with `id=999`. | Returns `None`. |
| **TC-SRV-CUST-07** | `get_all_customers` | Pagination limits: Retrieve customers with explicit limit and offset boundaries. | 5 customers exist in DB. Retrieve with `limit=2`, `offset=2`. | Returns exactly 2 customer responses corresponding to indices 2 and 3. |
| **TC-SRV-CUST-08** | `get_active_customers` | Filter Status: Retrieve active customers only. | 2 active customers, 1 inactive customer in DB. | Returns exactly 2 active customer records. Inactive record is omitted. |
| **TC-SRV-CUST-09** | `search_customers` | Search Partial Name: Search customers using a substring pattern. | Customers in DB: "Alice Cooper", "Bob Ross", "Alice in Wonderland". Search: `"Alice"`. | Returns "Alice Cooper" and "Alice in Wonderland" profiles. Case-insensitive. |
| **TC-SRV-CUST-10** | `search_customers` | Search No Matches: Search using a pattern that matches nothing. | Search: `"XYZ"`. | Returns an empty list `[]`. |
| **TC-SRV-CUST-11** | `update_customer` | Update Existing Customer: Modify fields of an existing customer. | Existing customer `id=1`. Update fields: `name="Alice Cooper"`, `email="cooper@example.com"`. | Customer details updated in database. Returns updated model with modified fields. |
| **TC-SRV-CUST-12** | `update_customer` | Update Non-Existent Customer: Try to update a customer profile that does not exist. | `customer_id=999`. | Returns `None`. |
| **TC-SRV-CUST-13** | `delete_customer` | Soft Delete: Set `is_active` to `False` instead of removing from DB. | Existing customer `id=1` with `is_active=True`. | `is_active` updated to `False` in DB. Customer data remains in DB. Returns `True`. |
| **TC-SRV-CUST-14** | `delete_customer` | Soft Delete Non-Existent Customer: Delete non-existent ID. | `customer_id=999`. | Returns `False`. |
| **TC-SRV-CUST-15** | `hard_delete_customer`| Hard Delete: Permanently remove the customer record from DB. | Existing customer `id=1`. | Customer record is deleted from DB. Returns `True`. |
| **TC-SRV-CUST-16** | `hard_delete_customer`| Hard Delete Non-Existent: Attempt permanent delete on missing ID. | `customer_id=999`. | Returns `False`. |

---

### 1.2 Customer Repository (`CustomerRepository`)

| Test Case ID | Target Method | Scenario Description | Inputs / Prerequisites | Expected Outcome / Assertions |
| :--- | :--- | :--- | :--- | :--- |
| **TC-REP-CUST-01** | `get_by_email` | Find customer by email. | DB contains email `"alice@example.com"`. | Returns SQLAlchemy model matching email. |
| **TC-REP-CUST-02** | `get_by_email` | Find customer by email (missing case). | Query `"unknown@example.com"`. | Returns `None`. |
| **TC-REP-CUST-03** | `get_active_customers` | Retrieve active customer instances. | 2 active, 2 inactive customer entities in database. | Returns list of length 2 containing active models. |
| **TC-REP-CUST-04** | `search_by_name` | Query using SQL `LIKE` operator matching name. | 1 customer matches `%Smith%`. | Returns matching model records. |

---

### 1.3 Customer API (`/api/v1/customers`)

| Test Case ID | HTTP Method / Route | Scenario Description | Payload / Query Params | Expected Status & Response |
| :--- | :--- | :--- | :--- | :--- |
| **TC-API-CUST-01** | `POST /api/v1/customers` | Valid creation payload. | `{"name": "Jack", "email": "jack@example.com"}` | **200 OK** / Returns populated `CustomerResponse`. |
| **TC-API-CUST-02** | `POST /api/v1/customers` | Invalid Email Format. | `{"name": "Jack", "email": "invalid-email"}` | **422 Unprocessable Entity** (Pydantic validation failure). |
| **TC-API-CUST-03** | `POST /api/v1/customers` | Duplicate email trigger. | `{"name": "Jack", "email": "existing@example.com"}` | **400 Bad Request** / `{"error": "ValueError", "message": "..."}`. |
| **TC-API-CUST-04** | `GET /api/v1/customers/{id}` | Fetch customer by valid ID. | `id = 1` | **200 OK** / Returns customer object. |
| **TC-API-CUST-05** | `GET /api/v1/customers/{id}` | Fetch customer by missing ID. | `id = 999` | **404 Not Found** / `{"detail": "Customer 999 not found"}`. |
| **TC-API-CUST-06** | `PUT /api/v1/customers/{id}` | Update existing customer details. | `id = 1`, `{"name": "Updated", "email": "up@example.com"}` | **200 OK** / Returns updated customer fields. |
| **TC-API-CUST-07** | `DELETE /api/v1/customers/{id}` | Soft delete customer. | `id = 1` | **200 OK** / `{"message": "Customer 1 deleted successfully"}`. |
| **TC-API-CUST-08** | `GET /api/v1/customers` | Pagination index boundary checking. | `limit=-1`, `offset=-5` | **422 Unprocessable Entity** (Query bounds violations: `ge=1`, `ge=0`). |

---
---

## 2. Product Module Test Cases

### 2.1 Product Service (`ProductService`)

| Test Case ID | Target Method | Scenario Description | Inputs / Prerequisites | Expected Outcome / Assertions |
| :--- | :--- | :--- | :--- | :--- |
| **TC-SRV-PROD-01** | `create_product` | Happy Path: Create product with stock > 0. | `name="Laptop"`, `base_price=99.99`, `stock_quantity=5`. | Created with `is_available=True`, returns `ProductResponse`. |
| **TC-SRV-PROD-02** | `create_product` | Edge Path: Create product with stock = 0. | `name="Out of Stock Item"`, `base_price=5.00`, `stock_quantity=0`. | Created with `is_available=False`. |
| **TC-SRV-PROD-03** | `update_stock` | Increase Stock: Add inventory. | Existing product with stock 10. `quantity_change=5`. | Stock becomes 15; `is_available=True`. |
| **TC-SRV-PROD-04** | `update_stock` | Deplete Stock: Remove inventory exactly to 0. | Existing product with stock 5. `quantity_change=-5`. | Stock becomes 0; `is_available` transitions to `False`. |
| **TC-SRV-PROD-05** | `update_stock` | Deplete Stock: Remove inventory below 0. | Existing product with stock 2. `quantity_change=-5`. | Depends on DB constraint or repo logic. Repo allows negative or clamps? If database allows, check value. |
| **TC-SRV-PROD-06** | `update_stock` | Non-Existent Product: Adjust stock for invalid ID. | `product_id=999`, `quantity_change=10`. | Returns `None`. |
| **TC-SRV-PROD-07** | `check_availability`| In-Stock Check: Query available stock vs requested quantity. | Product exists with stock 10. Request `quantity=5`. | Returns `True`. |
| **TC-SRV-PROD-08** | `check_availability`| Insufficient Stock Check: Query quantity > stock. | Product exists with stock 10. Request `quantity=11`. | Returns `False`. |
| **TC-SRV-PROD-09** | `check_availability`| Unavailable Product Check: Query product with `is_available=False`. | Product exists with stock 5, `is_available=False`. Request `quantity=1`. | Returns `False`. |
| **TC-SRV-PROD-10** | `get_products_by_price_range`| Fetch by Price Boundaries. | Products at $10, $50, $100. Query `min_price=10.00`, `max_price=50.00`. | Returns the $10 and $50 products. |

---

### 2.2 Product Repository (`ProductRepository`)

| Test Case ID | Target Method | Scenario Description | Inputs / Prerequisites | Expected Outcome / Assertions |
| :--- | :--- | :--- | :--- | :--- |
| **TC-REP-PROD-01** | `get_available_products` | Return available instances. | In-stock and out-of-stock products in DB. | Returns models where `is_available=True` and `stock_quantity > 0`. |
| **TC-REP-PROD-02** | `update_stock` | Row-level DB atomic modification. | Product ID `1`, `change=-3`. | Product quantity updated in database atomically. Returns updated product instance. |
| **TC-REP-PROD-03** | `get_products_by_price_range` | Check min/max values filtering. | Query range $0.00 to $10.00. | Returns list of products matching the constraint. |

---

### 2.3 Product API (`/api/v1/products`)

| Test Case ID | HTTP Method / Route | Scenario Description | Payload / Query Params | Expected Status & Response |
| :--- | :--- | :--- | :--- | :--- |
| **TC-API-PROD-01** | `POST /api/v1/products` | Create product with negative price. | `{"name": "Box", "base_price": -1.50}` | **422 Unprocessable Entity** (Pydantic validator `gt=0` failure). |
| **TC-API-PROD-02** | `POST /api/v1/products` | Create product with valid price. | `{"name": "Box", "base_price": 5.99, "stock_quantity": 10}` | **200 OK** / Returns product JSON. |
| **TC-API-PROD-03** | `GET /api/v1/products/available`| Get all available products. | None | **200 OK** / Returns list. |
| **TC-API-PROD-04** | `PATCH /api/v1/products/{id}/stock` | Update stock quantity. | `id = 1`, query param `change = 10` | **200 OK** / Returns updated product. |
| **TC-API-PROD-05** | `PATCH /api/v1/products/{id}/stock` | Update stock for missing product ID. | `id = 999`, query param `change = 5` | **404 Not Found** / Exception handled. |

---
---

## 3. Order Module Test Cases

### 3.1 Order Service (`OrderService`)

```
State Flow: PENDING -> ACCEPTED / REJECTED -> INVOICED -> PAID -> SHIPPED -> COMPLETED
```

| Test Case ID | Target Method | Scenario Description | Inputs / Prerequisites | Expected Outcome / Assertions |
| :--- | :--- | :--- | :--- | :--- |
| **TC-SRV-ORD-01** | `create_order` | Happy Path: Successfully place an order with multiple valid products. | Customer `id=1` exists. Product `id=1` (price $10.00, stock 5), Product `id=2` (price $20.00, stock 10). Request items: `[{"product_id": 1, "quantity": 2}, {"product_id": 2, "quantity": 1}]`. | 1. Order status set to `PENDING`. <br>2. Total price is calculated as $(10 \times 2) + (20 \times 1) = \$40.00$. <br>3. Product stock updated: Product 1 stock becomes 3, Product 2 stock becomes 9. <br>4. Returns `OrderResponse`. |
| **TC-SRV-ORD-02** | `create_order` | Edge Path: Non-existent product ID. | Request items: `[{"product_id": 999, "quantity": 1}]`. | Raises `ValueError` ("Product 999 not found"). Product stock for other items is unaffected (atomic transaction). |
| **TC-SRV-ORD-03** | `create_order` | Edge Path: Product is not available (`is_available=False`). | Product `id=1` has `is_available=False`. Request: `[{"product_id": 1, "quantity": 1}]`. | Raises `ValueError` ("Product 1 is not available"). Stock is not modified. |
| **TC-SRV-ORD-04** | `create_order` | Edge Path: Insufficient stock. | Product `id=1` has stock 2. Request `quantity=3`. | Raises `ValueError` ("Insufficient stock for product 1. Available: 2, Requested: 3"). Stock is not modified. |
| **TC-SRV-ORD-05** | `review_order` | Accept Order: Move order from `PENDING` to `ACCEPTED`. | Order `id=1` with status `PENDING`. | Status set to `ACCEPTED`. Notes updated. |
| **TC-SRV-ORD-06** | `review_order` | Reject Order: Move order from `PENDING` to `REJECTED` and restore stock. | Order `id=1` (status `PENDING`) with line items: Product 1 (qty 2). Product 1 current stock = 3. | 1. Order status set to `REJECTED`. <br>2. Product 1 stock is restored to 5 (3 + 2). <br>3. Returns updated order details. |
| **TC-SRV-ORD-07** | `review_order` | Review Non-Pending Order: Try to accept an order that is already in another state. | Order `id=1` with status `ACCEPTED`. | Raises `ValueError` ("Order 1 is not in PENDING status"). |
| **TC-SRV-ORD-08** | `ship_order` | Happy Path: Ship a paid order. | Order `id=1` with status `PAID`. | Status set to `SHIPPED`. `shipped_at` timestamp is set to the current time. |
| **TC-SRV-ORD-09** | `ship_order` | Ship Unpaid Order: Try to ship an order with status `ACCEPTED`. | Order `id=1` with status `ACCEPTED`. | Raises `ValueError` ("Order 1 is not in PAID status"). |
| **TC-SRV-ORD-10** | `complete_order` | Happy Path: Complete a shipped order. | Order `id=1` with status `SHIPPED`. | Status set to `COMPLETED`. `completed_at` timestamp is set. |
| **TC-SRV-ORD-11** | `complete_order` | Complete Unshipped Order: Try to complete an order with status `PAID`. | Order `id=1` with status `PAID`. | Raises `ValueError` ("Order 1 is not in SHIPPED status"). |
| **TC-SRV-ORD-12** | `cancel_order` | Cancel Before Shipping: Cancel an `INVOICED` order. | Order `id=1` (status `INVOICED`) with items: Product 1 (qty 2). Current stock of Product 1 = 3. | Order status transitions to `CANCELLED`. Stock of Product 1 is restored to 5. |
| **TC-SRV-ORD-13** | `cancel_order` | Cancel After Shipping Failure: Try to cancel a `SHIPPED` order. | Order `id=1` with status `SHIPPED`. | Raises `ValueError` ("Order 1 cannot be cancelled after shipping"). Stock is not modified. |
| **TC-SRV-ORD-14** | `cancel_order` | Cancel Completed Order: Try to cancel a `COMPLETED` order. | Order `id=1` with status `COMPLETED`. | Raises `ValueError` ("Order 1 cannot be cancelled after shipping"). |
| **TC-SRV-ORD-15** | `get_orders_for_shipping` | Fetch paid orders ready to ship. | Orders in status `PAID` and `ACCEPTED`. | Returns orders with status `PAID` only. |
| **TC-SRV-ORD-16** | `get_total_revenue` | Aggregate revenue from database. | Completed order ($100), Shipped order ($50), Cancelled order ($20) exist in database. | Returns total revenue = $100.00 (completed orders only). |

---

### 3.2 Order Repository (`OrderRepository`)

| Test Case ID | Target Method | Scenario Description | Inputs / Prerequisites | Expected Outcome / Assertions |
| :--- | :--- | :--- | :--- | :--- |
| **TC-REP-ORD-01** | `get_with_line_items`| Eagerly load relationship collections. | Order ID `1` exists with multiple items. | Returns order model; accessing `.line_items` and `.line_items[0].product` succeeds without additional database queries. |
| **TC-REP-ORD-02** | `get_orders_by_customer`| Retrieve user's order history. | Customer ID `1` has 3 orders. | Returns 3 orders sorted by `created_at` in descending order. |
| **TC-REP-ORD-03** | `get_orders_in_date_range`| Query using date window boundaries. | Orders created yesterday, today, and tomorrow. | Query with start/end of today returns today's orders only. |

---

### 3.3 Order API (`/api/v1/orders`)

| Test Case ID | HTTP Method / Route | Scenario Description | Payload / Query Params | Expected Status & Response |
| :--- | :--- | :--- | :--- | :--- |
| **TC-API-ORD-01** | `POST /api/v1/orders` | Successful placement. | `{"customer_id": 1, "line_items": [{"product_id": 1, "quantity": 1}]}` | **200 OK** / Returns order response details. |
| **TC-API-ORD-02** | `POST /api/v1/orders` | Place order with empty line items. | `{"customer_id": 1, "line_items": []}` | **422 Unprocessable Entity** (Pydantic rule: `min_length=1`). |
| **TC-API-ORD-03** | `POST /api/v1/orders/{id}/review` | Accept order via staff endpoint. | `id = 1`, query params `accept=true` | **200 OK** / Status updated to `accepted`. |
| **TC-API-ORD-04** | `POST /api/v1/orders/{id}/review` | Reject order via staff endpoint. | `id = 1`, query params `accept=false` | **200 OK** / Status updated to `rejected`. |
| **TC-API-ORD-05** | `POST /api/v1/orders/{id}/ship` | Ship unpaid order error. | `id = 1` (order is in `accepted` status) | **400 Bad Request** / Error details returned. |
| **TC-API-ORD-06** | `POST /api/v1/orders/{id}/cancel` | Cancel order after it is completed. | `id = 1` (order is in `completed` status) | **400 Bad Request** / Error details returned. |

---
---

## 4. Payment Module Test Cases

### 4.1 Payment Service (`PaymentService`)

| Test Case ID | Target Method | Scenario Description | Inputs / Prerequisites | Expected Outcome / Assertions |
| :--- | :--- | :--- | :--- | :--- |
| **TC-SRV-PAY-01** | `create_payment` | Happy Path: Create payment for invoiced order. | Order `id=1` exists with status `INVOICED`. Payment amount = $50.00. | Returns new `PaymentResponse` with status `PENDING`. |
| **TC-SRV-PAY-02** | `create_payment` | Edge Path: Create payment for accepted order. | Order `id=1` exists with status `ACCEPTED`. | Returns new `PaymentResponse` with status `PENDING`. |
| **TC-SRV-PAY-03** | `create_payment` | Edge Path: Invalid Order Status. | Order `id=1` is in `PENDING` status. | Raises `ValueError` ("Order 1 is not in a payable status. Current status: pending"). |
| **TC-SRV-PAY-04** | `create_payment` | Edge Path: Order not found. | Order `id=999` does not exist. | Raises `ValueError` ("Order 999 not found"). |
| **TC-SRV-PAY-05** | `verify_payment` | Complete Payment (Exact Amount): Verify payment that matches order total. | Order `id=1` total amount = $100.00. Payment `id=1` amount = $100.00. | 1. Payment status set to `COMPLETED`. <br>2. `processed_at` is set. <br>3. Linked Order status updated to `PAID`. <br>4. Returns verified payment. |
| **TC-SRV-PAY-06** | `verify_payment` | Complete Payment (Multiple Payments): Verify payment that pushes total paid >= order total. | Order `id=1` total = $100.00. Completed payment 1 = $40.00. Pending payment 2 = $60.00. Verify payment 2. | 1. Payment 2 status set to `COMPLETED`. <br>2. Linked Order status updated to `PAID`. |
| **TC-SRV-PAY-07** | `verify_payment` | Partial Payment: Verify payment that is less than order total. | Order `id=1` total = $100.00. Payment `id=1` amount = $30.00. Verify payment 1. | 1. Payment status set to `PROCESSING`. <br>2. Linked Order status remains `INVOICED` (not updated to PAID). |
| **TC-SRV-PAY-08** | `verify_payment` | Already Verified Payment: Attempt to verify a completed payment. | Payment `id=1` has status `COMPLETED`. | Raises `ValueError` ("Payment 1 is not in PENDING status"). |
| **TC-SRV-PAY-09** | `fail_payment` | Mark Payment as Failed: Roll back status. | Order `id=1` is `INVOICED`. Payment `id=1` status is `PENDING`. | 1. Payment status set to `FAILED`. <br>2. Order status reset to `ACCEPTED` (so it can be re-invoiced or paid again). |
| **TC-SRV-PAY-10** | `refund_payment` | Refund Paid Order: Refund a completed payment. | Order `id=1` total = $100.00. Payment `id=1` is `COMPLETED`. Order status is `PAID` (or `SHIPPED`). | 1. Payment status set to `REFUNDED`. <br>2. Linked Order status set to `CANCELLED`. |
| **TC-SRV-PAY-11** | `refund_payment` | Refund Uncompleted Payment: Try to refund a pending payment. | Payment `id=1` has status `PENDING`. | Raises `ValueError` ("Payment 1 is not completed"). |

---

### 4.2 Payment Repository (`PaymentRepository`)

| Test Case ID | Target Method | Scenario Description | Inputs / Prerequisites | Expected Outcome / Assertions |
| :--- | :--- | :--- | :--- | :--- |
| **TC-REP-PAY-01** | `get_total_paid_amount`| Sum verified payments. | 2 completed payments ($50, $30) and 1 failed payment ($20) for order 1. | Returns float total = 80.0. |
| **TC-REP-PAY-02** | `get_pending_payments`| Retrieve pending verifications. | Multiple payments with status `pending` and `completed`. | Returns list containing only `pending` status payments. |
| **TC-REP-PAY-03** | `get_by_transaction_id`| Look up transaction code. | Payment exists with transaction ID `"TXN-12345"`. | Returns payment record matching transaction ID. |

---

### 4.3 Payment API (`/api/v1/payments`)

| Test Case ID | HTTP Method / Route | Scenario Description | Payload / Query Params | Expected Status & Response |
| :--- | :--- | :--- | :--- | :--- |
| **TC-API-PAY-01** | `POST /api/v1/payments` | Submit new payment. | `{"order_id": 1, "amount": 100.00, "method": "card", "transaction_id": "T1"}` | **200 OK** / Returns payment response. |
| **TC-API-PAY-02** | `POST /api/v1/payments` | Submit payment with negative amount. | `{"order_id": 1, "amount": -10.00, "method": "card"}` | **422 Unprocessable Entity** (Pydantic `gt=0` validation failure). |
| **TC-API-PAY-03** | `POST /api/v1/payments/{id}/verify`| Verify payment (Accountant). | `id = 1` | **200 OK** / Returns updated status object. |
| **TC-API-PAY-04** | `POST /api/v1/payments/{id}/verify`| Verify payment (Missing payment ID).| `id = 999` | **404 Not Found** / Error message. |

---
---

## 5. Invoice Module Test Cases

### 5.1 Invoice Service (`InvoiceService`)

| Test Case ID | Target Method | Scenario Description | Inputs / Prerequisites | Expected Outcome / Assertions |
| :--- | :--- | :--- | :--- | :--- |
| **TC-SRV-INV-01** | `create_invoice` | Happy Path: Create invoice for accepted order. | Order `id=1` (status `ACCEPTED`, total = $100.00). Invoice request: `tax_rate=0.10`, `due_date="2026-12-31"`. | 1. Invoice generated with unique number format: `INV-YYYYMMDD-XXXX`. <br>2. Subtotal = $100.00, Tax = $10.00, Total = $110.00. <br>3. Linked Order status transitions to `INVOICED`. <br>4. Linked Order `invoice_id` set to generated invoice ID. <br>5. Returns `InvoiceResponse`. |
| **TC-SRV-INV-02** | `create_invoice` | Edge Path: Order not in ACCEPTED state. | Order `id=1` is in `PENDING` state. | Raises `ValueError` ("Order 1 is not in ACCEPTED status. Current status: pending"). |
| **TC-SRV-INV-03** | `create_invoice` | Edge Path: Invoice already exists. | Order `id=1` is `ACCEPTED` but already has an invoice record linked in DB. | Raises `ValueError` ("Invoice already exists for order 1"). |
| **TC-SRV-INV-04** | `cancel_invoice` | Happy Path: Cancel issued invoice. | Invoice `id=1` (status `ISSUED`) linked to Order `id=1` (status `INVOICED`). | 1. Invoice status set to `CANCELLED`. <br>2. Linked Order status set to `ACCEPTED`. <br>3. Linked Order `invoice_id` cleared to `None`. <br>4. Returns cancelled invoice object. |
| **TC-SRV-INV-05** | `cancel_invoice` | Cancel Paid Invoice Failure: Prevent cancellation. | Invoice `id=1` status is `PAID`. | Raises `ValueError` ("Cannot cancel a paid invoice"). |
| **TC-SRV-INV-06** | `check_and_update_overdue`| Identify and update overdue invoices. | 2 invoices in DB with status `ISSUED` and `due_date` in the past. 1 invoice with status `PAID` and `due_date` in the past. | 1. The 2 `ISSUED` invoices are updated to status `OVERDUE` in DB. <br>2. The `PAID` invoice remains unchanged. <br>3. Returns `2` (count of updated invoices). |

---

### 5.2 Invoice Repository (`InvoiceRepository`)

| Test Case ID | Target Method | Scenario Description | Inputs / Prerequisites | Expected Outcome / Assertions |
| :--- | :--- | :--- | :--- | :--- |
| **TC-REP-INV-01** | `get_by_order` | Find invoice by linked order ID. | Invoice exists for order ID `1`. | Returns the invoice model object. |
| **TC-REP-INV-02** | `get_by_invoice_number`| Retrieve using unique billing number. | Invoice exists with number `"INV-20260707-1234"`. | Returns matching invoice model. |
| **TC-REP-INV-03** | `get_overdue_invoices` | Find unpaid past-due invoices. | Query overdue items relative to current timestamp. | Returns invoices where `due_date` < current timestamp and status is `ISSUED`. |

---

### 5.3 Invoice API (`/api/v1/invoices`)

| Test Case ID | HTTP Method / Route | Scenario Description | Payload / Query Params | Expected Status & Response |
| :--- | :--- | :--- | :--- | :--- |
| **TC-API-INV-01** | `POST /api/v1/invoices` | Create new invoice. | `{"order_id": 1, "billing_name": "Alice", "tax_rate": 0.10, "due_date": "2026-12-31T00:00:00"}` | **200 OK** / Returns invoice response metadata. |
| **TC-API-INV-02** | `POST /api/v1/invoices` | Invoice creation validation (invalid tax rate). | `{"order_id": 1, "billing_name": "Alice", "tax_rate": 1.50, "due_date": "2026-12-31T00:00:00"}` | **422 Unprocessable Entity** (Pydantic validator `le=1` failure). |
| **TC-API-INV-03** | `POST /api/v1/invoices/{id}/cancel` | Cancel existing invoice. | `id = 1` | **200 OK** / Status updated to `cancelled`. |
| **TC-API-INV-04** | `GET /api/v1/invoices/overdue` | Retrieve list of overdue invoices. | None | **200 OK** / Returns overdue list. |

---
---

## 6. System & Infrastructure Edge Cases

### 6.1 Database Transactions & Concurrency

| Test Case ID | Scenario Description | Inputs / Prerequisites | Expected Outcome / Assertions |
| :--- | :--- | :--- | :--- |
| **TC-SYS-CONC-01** | **Race Condition on Stock Allocation** | Product stock count = `1`. Two clients concurrently submit orders for quantity `1` of this product. | One transaction commits successfully (order placed, stock becomes `0`). The second transaction fails validation with `ValueError` (insufficient stock) and rolls back cleanly without causing negative stock values. |
| **TC-SYS-CONC-02** | **Double Payment Submission** | Payment status is `PENDING` for order `1` (total $100). Two processing threads attempt to call `verify_payment` for the same payment transaction ID simultaneously. | The database row-level locking or unique transaction constraints ensure only one verification thread completes successfully. The second thread receives a `ValueError` indicating the payment is already completed or processed, preventing double-crediting. |
| **TC-SYS-TX-01** | **Database Failure on Mid-Order Creation** | Customer creates order. Order object is written, but database connection drops before line items or stock updates are written. | The database transaction rolls back completely. No orphaned `Order` records are left without line items, and product stock remains unaltered. |
| **TC-SYS-ERR-01** | **Global Exception Catching** | API encounters an unhandled runtime error (e.g. database connection timeout). | Global middleware exception handler catches the crash and returns an HTTP `500 Internal Server Error` with JSON structure matching `ErrorResponse`, masking raw traceback leaks. |
