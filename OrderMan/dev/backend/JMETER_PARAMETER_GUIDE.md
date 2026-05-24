# JMeter Parameter and Dynamic Data Guide

## Overview
This guide shows how to handle dynamic parameters, IDs, and request bodies in Apache JMeter for API testing.

## Methods for Dynamic Parameters

### 1. **JSON Extractor** (Most Common)
Extract values from JSON responses to use in subsequent requests.

#### Setup JSON Extractor:
1. Add **JSON Extractor** as a child of the HTTP Request
2. Configure:
   - **Variable Name**: `CUSTOMER_ID`
   - **JSON Path Expression**: `$.id`
   - **Match No.**: `1` (first match)
   - **Default Value**: `NOT_FOUND`

#### Example Flow:
```
POST /api/customers (Create Customer)
├── JSON Extractor: Extract $.id as CUSTOMER_ID
└── Response: {"id": 123, "name": "John Doe", ...}

GET /api/customers/${CUSTOMER_ID} (Use extracted ID)
└── Actual URL: /api/customers/123
```

### 2. **Regular Expression Extractor**
For non-JSON responses or complex extraction patterns.

#### Configuration:
- **Reference Name**: `ORDER_ID`
- **Regular Expression**: `"id":(\d+)`
- **Template**: `$1$`
- **Match No.**: `1`

### 3. **User Defined Variables**
For static or semi-static values.

#### Setup:
1. Right-click Test Plan → Add → Config Element → User Defined Variables
2. Add variables:
   - `BASE_URL`: `http://localhost:3000/api`
   - `DEFAULT_CUSTOMER_ID`: `1`
   - `TEST_PHONE_PREFIX`: `555-`

### 4. **CSV Data Set Config**
For testing with multiple data sets.

#### Setup:
1. Create CSV file: `test-data.csv`
```csv
customer_name,customer_phone,customer_address
John Doe,555-0101,123 Main St
Jane Smith,555-0102,456 Oak Ave
Bob Johnson,555-0103,789 Pine Rd
```

2. Add CSV Data Set Config:
   - **Filename**: `test-data.csv`
   - **Variable Names**: `customer_name,customer_phone,customer_address`
   - **Delimiter**: `,`

## Practical Examples

### Example 1: Complete Workflow with Dynamic IDs

#### Step 1: Create Customer
**HTTP Request**:
- **Method**: POST
- **Path**: `/api/customers`
- **Body**:
```json
{
  "name": "${customer_name}",
  "address": "${customer_address}",
  "phone": "${customer_phone}",
  "bankAccount": "12345${__threadNum}"
}
```

**JSON Extractor** (Child of above request):
- **Variable Name**: `CUSTOMER_ID`
- **JSON Path**: `$.id`
- **Default Value**: `ERROR`

#### Step 2: Create Order Using Customer ID
**HTTP Request**:
- **Method**: POST
- **Path**: `/api/orders`
- **Body**:
```json
{
  "customerId": ${CUSTOMER_ID},
  "customerName": "${customer_name}",
  "customerAddress": "${customer_address}",
  "customerPhone": "${customer_phone}",
  "totalAmount": 99.99,
  "method": "card",
  "items": [
    {
      "name": "Test Product",
      "quantity": 1,
      "price": 99.99
    }
  ]
}
```

**JSON Extractor**:
- **Variable Name**: `ORDER_ID`
- **JSON Path**: `$.id`

#### Step 3: Accept Order
**HTTP Request**:
- **Method**: POST
- **Path**: `/api/orders/${ORDER_ID}/receive`
- **Body**: (empty)

#### Step 4: Create Invoice
**HTTP Request**:
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

**JSON Extractor**:
- **Variable Name**: `INVOICE_ID`
- **JSON Path**: `$.id`

#### Step 5: Send Invoice
**HTTP Request**:
- **Method**: POST
- **Path**: `/api/invoices/send/${ORDER_ID}`

#### Step 6: Create Payment
**HTTP Request**:
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

**JSON Extractor**:
- **Variable Name**: `PAYMENT_ID`
- **JSON Path**: `$.id`

#### Step 7: Accept Payment (Key Step!)
**HTTP Request**:
- **Method**: POST
- **Path**: `/api/payments/accept/${PAYMENT_ID}`
- **Body**: (empty)

### Example 2: Using Functions for Dynamic Data

#### Random Data Generation
```json
{
  "name": "Customer_${__Random(1000,9999)}",
  "phone": "555-${__Random(1000,9999)}",
  "email": "test${__threadNum}@example.com",
  "timestamp": "${__time(yyyy-MM-dd HH:mm:ss)}"
}
```

#### Common JMeter Functions:
- `${__threadNum}` - Current thread number
- `${__Random(1,100)}` - Random number between 1-100
- `${__time(yyyy-MM-dd)}` - Current date/time
- `${__UUID()}` - Generate UUID
- `${__counter(TRUE)}` - Incrementing counter

### Example 3: Conditional Parameters

#### Using If Controller
1. Add **If Controller**
2. Condition: `"${CUSTOMER_ID}" != "ERROR"`
3. Add requests that depend on successful customer creation

#### Using Response Assertion
1. Add **Response Assertion** to check if ID was extracted
2. **Field to Test**: Variable
3. **Variable Name**: `CUSTOMER_ID`
4. **Pattern Matching Rules**: Matches
5. **Patterns to Test**: `\d+` (numeric ID)

## Advanced Techniques

### 1. **BeanShell PostProcessor**
For complex data manipulation:

```javascript
// Extract and modify data
String responseData = prev.getResponseDataAsString();
String customerId = vars.get("CUSTOMER_ID");

// Create complex derived values
vars.put("FULL_CUSTOMER_PATH", "/api/customers/" + customerId);
vars.put("ORDER_REFERENCE", "ORD-" + customerId + "-" + System.currentTimeMillis());

log.info("Customer ID extracted: " + customerId);
```

### 2. **JSR223 PostProcessor** (Recommended over BeanShell)
```groovy
// Groovy script for data processing
def customerId = vars.get("CUSTOMER_ID")
def orderTotal = (Math.random() * 1000).round(2)

vars.put("ORDER_TOTAL", orderTotal.toString())
vars.put("TAX_AMOUNT", (orderTotal * 0.08).round(2).toString())

log.info("Generated order total: ${orderTotal}")
```

### 3. **Multiple Extractors from Same Response**
```json
// Response: {"id": 123, "status": "pending", "total": 99.99}
```

Add multiple JSON Extractors:
1. **Extractor 1**: `$.id` → `ORDER_ID`
2. **Extractor 2**: `$.status` → `ORDER_STATUS`  
3. **Extractor 3**: `$.total` → `ORDER_TOTAL`

## Error Handling

### 1. **Default Values**
Always set default values in extractors:
- **Default Value**: `NOT_FOUND` or `ERROR`

### 2. **Validation**
Add **If Controller** to check extracted values:
```javascript
"${CUSTOMER_ID}" != "NOT_FOUND" && "${CUSTOMER_ID}" != ""
```

### 3. **Debug Sampler**
Add **Debug Sampler** to see all variables:
- Shows all JMeter variables and their values
- Useful for troubleshooting extraction issues

## Testing Specific Scenarios

### Scenario 1: Test with Existing IDs
**User Defined Variables**:
- `EXISTING_CUSTOMER_ID`: `1`
- `EXISTING_ORDER_ID`: `5`
- `EXISTING_INVOICE_ID`: `3`

**HTTP Request**:
- **Path**: `/api/customers/${EXISTING_CUSTOMER_ID}`

### Scenario 2: Test Error Cases
**HTTP Request**:
- **Path**: `/api/customers/99999` (non-existent ID)

**Response Assertion**:
- **Response Code**: `404`

### Scenario 3: Parameterized Testing
**CSV Data**: `order-test-data.csv`
```csv
customer_id,product_name,quantity,price,expected_total
1,Laptop,1,999.99,999.99
2,Mouse,2,29.99,59.98
3,Keyboard,1,149.99,149.99
```

**HTTP Request Body**:
```json
{
  "customerId": ${customer_id},
  "items": [
    {
      "name": "${product_name}",
      "quantity": ${quantity},
      "price": ${price}
    }
  ],
  "totalAmount": ${expected_total}
}
```

## Best Practices

### 1. **Variable Naming**
- Use descriptive names: `CUSTOMER_ID`, `ORDER_ID`, `PAYMENT_ID`
- Use consistent prefixes: `TEST_`, `TEMP_`, `EXTRACTED_`

### 2. **Error Handling**
- Always set default values in extractors
- Add validation controllers
- Use debug samplers for troubleshooting

### 3. **Data Management**
- Use CSV files for large datasets
- Use functions for dynamic data generation
- Clean up variables when no longer needed

### 4. **Performance**
- Extract only needed values
- Use efficient JSON paths
- Avoid complex regular expressions in high-load tests

## Common Patterns for Your API

### Pattern 1: Entity Creation Chain
```
Create Customer → Extract ID → Create Order → Extract ID → Create Invoice
```

### Pattern 2: Status Progression Testing
```
Create Order → Check Status=pending → Accept Order → Check Status=accepted
```

### Pattern 3: Relationship Testing
```
Create Customer → Create Multiple Orders → Verify Customer-Order Relationship
```

This approach ensures your JMeter tests can handle the dynamic nature of your API while maintaining realistic test scenarios.