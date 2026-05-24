# Apache JMeter API Testing Guide

## Overview
This guide provides comprehensive Apache JMeter test plans for all API endpoints in the application.

**Base URL**: `http://localhost:3000/api`

## Complete API Endpoints Inventory

### Customer API (`/api/customers`)
- `GET /` - Get all customers
- `GET /:id` - Get customer by ID
- `GET /orders` - Get all orders (via customer controller)
- `POST /` - Create new customer
- `POST /orders` - Create new order (via customer controller)
- `PUT /:id` - Update customer by ID
- `DELETE /:id` - Delete customer by ID
- `DELETE /orders/:id` - Delete order by ID (via customer controller)

### Product API (`/api/products`)
- `GET /` - Get all products
- `GET /:id` - Get product by ID
- `POST /` - Create new product
- `PUT /:id` - Update product by ID
- `DELETE /:id` - Delete product by ID

### Order API (`/api/orders`)
- `GET /` - Get all orders
- `GET /:id` - Get order by ID
- `GET /user/:userId` - Get orders by customer ID
- `POST /` - Create new order
- `POST /:id/receive` - Mark order as received (accept)
- `POST /:id/ship` - Mark order as shipped
- `POST /:id/close` - Mark order as closed
- `PUT /:id` - Update order by ID
- `DELETE /:id` - Delete order by ID

### Invoice API (`/api/invoices`)
- `GET /` - Get all invoices
- `GET /:id` - Get invoice by ID
- `GET /order/:orderId` - Get invoices by order ID
- `POST /` - Create new invoice
- `POST /send/:orderId` - Send invoice for order
- `PUT /:id` - Update invoice by ID
- `DELETE /:id` - Delete invoice by ID

### Payment API (`/api/payments`)
- `GET /` - Get all payments
- `GET /:id` - Get payment by ID
- `GET /invoices/:invoiceId` - Get payments by invoice ID
- `POST /` - Create new payment
- `POST /accept/:id` - Accept payment by ID
- `PUT /:id` - Update payment by ID
- `DELETE /:id` - Delete payment by ID

## JMeter Test Plan Structure

### 1. Test Plan Setup

1. **Create New Test Plan**
   - Name: "E-Commerce API Test Plan"
   - Add User Defined Variables:
     - `BASE_URL`: `http://localhost:3000/api`
     - `CUSTOMER_ID`: `1` (will be set dynamically)
     - `ORDER_ID`: `1` (will be set dynamically)
     - `INVOICE_ID`: `1` (will be set dynamically)
     - `PAYMENT_ID`: `1` (will be set dynamically)
     - `PRODUCT_ID`: `1` (will be set dynamically)

### 2. Thread Groups

Create separate thread groups for each workflow:

#### Thread Group 1: Customer Management
- **Threads**: 5
- **Ramp-up**: 10 seconds
- **Loop Count**: 1

#### Thread Group 2: Product Management
- **Threads**: 3
- **Ramp-up**: 5 seconds
- **Loop Count**: 1

#### Thread Group 3: Complete Order Workflow
- **Threads**: 2
- **Ramp-up**: 5 seconds
- **Loop Count**: 1

### 3. HTTP Request Defaults

Add HTTP Request Defaults to each Thread Group:
- **Server Name**: `localhost`
- **Port**: `3000`
- **Protocol**: `http`
- **Content Encoding**: `utf-8`

### 4. HTTP Header Manager

Add to each Thread Group:
- **Content-Type**: `application/json`
- **Accept**: `application/json`

## Detailed Test Cases

### Customer API Tests

#### 1. Create Customer
- **Method**: POST
- **Path**: `/api/customers`
- **Body**:
```json
{
  "name": "Test Customer ${__threadNum}",
  "address": "123 Test Street",
  "phone": "555-010${__threadNum}",
  "bankAccount": "123456789${__threadNum}"
}
```
- **JSON Extractor**: Extract `id` as `CUSTOMER_ID`

#### 2. Get All Customers
- **Method**: GET
- **Path**: `/api/customers`

#### 3. Get Customer by ID
- **Method**: GET
- **Path**: `/api/customers/${CUSTOMER_ID}`

#### 4. Update Customer
- **Method**: PUT
- **Path**: `/api/customers/${CUSTOMER_ID}`
- **Body**:
```json
{
  "name": "Updated Customer ${__threadNum}",
  "phone": "555-999${__threadNum}"
}
```

#### 5. Delete Customer
- **Method**: DELETE
- **Path**: `/api/customers/${CUSTOMER_ID}`

### Product API Tests

#### 1. Create Product
- **Method**: POST
- **Path**: `/api/products`
- **Body**:
```json
{
  "name": "Test Product ${__threadNum}",
  "description": "A test product for JMeter testing",
  "price": ${__Random(10,100)}.99,
  "image": "https://via.placeholder.com/300x300?text=Product${__threadNum}"
}
```
- **JSON Extractor**: Extract `id` as `PRODUCT_ID`

#### 2. Get All Products
- **Method**: GET
- **Path**: `/api/products`

#### 3. Get Product by ID
- **Method**: GET
- **Path**: `/api/products/${PRODUCT_ID}`

#### 4. Update Product
- **Method**: PUT
- **Path**: `/api/products/${PRODUCT_ID}`
- **Body**:
```json
{
  "name": "Updated Product ${__threadNum}",
  "price": ${__Random(50,150)}.99
}
```

#### 5. Delete Product
- **Method**: DELETE
- **Path**: `/api/products/${PRODUCT_ID}`

### Complete Workflow Tests

#### 1. Create Order
- **Method**: POST
- **Path**: `/api/orders`
- **Body**:
```json
{
  "customerId": ${CUSTOMER_ID},
  "customerName": "Test Customer ${__threadNum}",
  "customerAddress": "123 Test Street",
  "customerPhone": "555-010${__threadNum}",
  "totalAmount": 99.99,
  "method": "card",
  "items": [
    {
      "productId": ${PRODUCT_ID},
      "name": "Test Product",
      "quantity": 2,
      "price": 49.99
    }
  ]
}
```
- **JSON Extractor**: Extract `id` as `ORDER_ID`

#### 2. Accept Order (Staff Action)
- **Method**: POST
- **Path**: `/api/orders/${ORDER_ID}/receive`

#### 3. Create Invoice
- **Method**: POST
- **Path**: `/api/invoices`
- **Body**:
```json
{
  "orderId": ${ORDER_ID},
  "amount": 99.99,
  "method": "card"
}
```
- **JSON Extractor**: Extract `id` as `INVOICE_ID`

#### 4. Send Invoice
- **Method**: POST
- **Path**: `/api/invoices/send/${ORDER_ID}`

#### 5. Create Payment
- **Method**: POST
- **Path**: `/api/payments`
- **Body**:
```json
{
  "invoiceId": ${INVOICE_ID},
  "amount": 99.99,
  "method": "card"
}
```
- **JSON Extractor**: Extract `id` as `PAYMENT_ID`

#### 6. Accept Payment (Accountant Action)
- **Method**: POST
- **Path**: `/api/payments/accept/${PAYMENT_ID}`

#### 7. Ship Order
- **Method**: POST
- **Path**: `/api/orders/${ORDER_ID}/ship`

#### 8. Close Order
- **Method**: POST
- **Path**: `/api/orders/${ORDER_ID}/close`

## Response Assertions

Add Response Assertions to each request:

### Success Assertions
- **Response Code**: `200`, `201`, or `204` (depending on endpoint)
- **Response Message**: `OK`, `Created`, or `No Content`

### JSON Response Assertions
For GET requests, assert JSON structure:
- **JSON Path**: `$.id` (exists)
- **JSON Path**: `$.name` (exists for entities with names)

### Workflow Assertions
- **Order Status Progression**: `pending` → `accepted` → `paid` → `shipped` → `closed`
- **Invoice Status**: `pending` → `issued` → `paid`
- **Payment Status**: `pending` → `completed`

## Listeners and Reporting

Add these listeners to monitor test execution:

1. **View Results Tree** - For debugging individual requests
2. **Summary Report** - For overall performance metrics
3. **Graph Results** - For response time visualization
4. **Aggregate Report** - For detailed statistics
5. **Simple Data Writer** - Save results to CSV for analysis

## Load Testing Scenarios

### Scenario 1: Normal Load
- **Users**: 10 concurrent users
- **Ramp-up**: 30 seconds
- **Duration**: 5 minutes

### Scenario 2: Peak Load
- **Users**: 50 concurrent users
- **Ramp-up**: 60 seconds
- **Duration**: 10 minutes

### Scenario 3: Stress Test
- **Users**: 100 concurrent users
- **Ramp-up**: 120 seconds
- **Duration**: 15 minutes

## Pre-Test Setup

1. **Start Backend Server**:
   ```bash
   cd dev/backend
   npm start
   ```

2. **Verify Server is Running**:
   ```bash
   curl http://localhost:3000/api/customers
   ```

3. **Database Setup**: Ensure your database is running and properly seeded

## Test Execution Order

1. **Setup Phase**: Create test data (customers, products)
2. **Workflow Phase**: Execute complete order workflows
3. **CRUD Phase**: Test individual CRUD operations
4. **Cleanup Phase**: Delete test data (optional)

## Expected Response Times

- **GET requests**: < 100ms
- **POST requests**: < 200ms
- **PUT requests**: < 150ms
- **DELETE requests**: < 100ms
- **Workflow operations**: < 300ms

## Error Scenarios to Test

1. **Invalid IDs**: Test with non-existent IDs (should return 404)
2. **Invalid JSON**: Test with malformed request bodies (should return 400)
3. **Missing Required Fields**: Test without required fields (should return 400)
4. **Workflow Violations**: Try to ship unaccepted orders (should return error)

## JMeter Configuration Files

Save your test plans as:
- `customer-api-tests.jmx`
- `product-api-tests.jmx`
- `order-workflow-tests.jmx`
- `complete-api-tests.jmx` (all endpoints)

## Monitoring and Analysis

Monitor these metrics during testing:
- **Response Times**: Average, 90th percentile, 95th percentile
- **Throughput**: Requests per second
- **Error Rate**: Percentage of failed requests
- **Server Resources**: CPU, Memory, Database connections

This comprehensive test plan will validate all API endpoints and ensure the complete workflow functions correctly under various load conditions.