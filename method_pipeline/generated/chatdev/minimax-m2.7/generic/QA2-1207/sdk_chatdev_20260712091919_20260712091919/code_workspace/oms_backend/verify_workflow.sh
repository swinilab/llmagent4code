#!/bin/bash
# OMS Backend - Complete Workflow Verification Script

set -e

BASE_URL="http://localhost:8000"
CUSTOMER_ID=""
ORDER_ID=""
INVOICE_ID=""
PAYMENT_ID=""

echo "=== OMS Backend Complete Workflow Verification ==="
echo ""

# Step 0: Check server health
echo "Step 0: Checking server health..."
curl -s "$BASE_URL/api/v1/health" | python -m json.tool
echo ""

# Step 1: Create a customer
echo "Step 1: Creating customer..."
CUSTOMER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/customers" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890",
    "address": {
      "street": "123 Main St",
      "city": "New York",
      "state": "NY",
      "postal_code": "10001",
      "country": "USA"
    }
  }')
echo "$CUSTOMER_RESPONSE" | python -m json.tool
CUSTOMER_ID=$(echo "$CUSTOMER_RESPONSE" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Customer ID: $CUSTOMER_ID"
echo ""

# Step 2: Create a product
echo "Step 2: Creating product..."
PRODUCT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/products" \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "PROD-001",
    "description": "Test Product",
    "base_price": 99.99,
    "stock_quantity": 100
  }')
echo "$PRODUCT_RESPONSE" | python -m json.tool
PRODUCT_ID=$(echo "$PRODUCT_RESPONSE" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Product ID: $PRODUCT_ID"
echo ""

# Step 3: Place order (Workflow Step 1)
echo "Step 3: Placing order..."
ORDER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/orders" \
  -H "Content-Type: application/json" \
  -d "{
    \"customer_id\": \"$CUSTOMER_ID\",
    \"line_items\": [
      {
        \"product_id\": \"$PRODUCT_ID\",
        \"product_description\": \"Test Product\",
        \"quantity\": 2,
        \"unit_price\": 99.99
      }
    ],
    \"shipping_address\": {
      \"street\": \"123 Main St\",
      \"city\": \"New York\",
      \"state\": \"NY\",
      \"postal_code\": \"10001\",
      \"country\": \"USA\"
    },
    \"idempotency_key\": \"order-key-$(date +%s)\"
  }")
echo "$ORDER_RESPONSE" | python -m json.tool
ORDER_ID=$(echo "$ORDER_RESPONSE" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Order ID: $ORDER_ID"
echo ""

# Step 4: Accept order (Workflow Step 2)
echo "Step 4: Accepting order..."
ACCEPT_RESPONSE=$(curl -s -X PATCH "$BASE_URL/api/v1/orders/$ORDER_ID/accept")
echo "$ACCEPT_RESPONSE" | python -m json.tool
echo ""

# Step 5: Create invoice (Workflow Step 3)
echo "Step 5: Creating invoice..."
INVOICE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/invoices" \
  -H "Content-Type: application/json" \
  -d "{
    \"order_id\": \"$ORDER_ID\",
    \"customer_id\": \"$CUSTOMER_ID\",
    \"billing_address\": {
      \"street\": \"123 Main St\",
      \"city\": \"New York\",
      \"state\": \"NY\",
      \"postal_code\": \"10001\",
      \"country\": \"USA\"
    }
  }")
echo "$INVOICE_RESPONSE" | python -m json.tool
INVOICE_ID=$(echo "$INVOICE_RESPONSE" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Invoice ID: $INVOICE_ID"
echo ""

# Step 6: Issue invoice
echo "Step 6: Issuing invoice..."
ISSUE_RESPONSE=$(curl -s -X PATCH "$BASE_URL/api/v1/invoices/$INVOICE_ID/issue")
echo "$ISSUE_RESPONSE" | python -m json.tool
echo ""

# Step 7: Create payment (Workflow Step 4)
echo "Step 7: Creating payment..."
PAYMENT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/payments" \
  -H "Content-Type: application/json" \
  -d "{
    \"order_id\": \"$ORDER_ID\",
    \"invoice_id\": \"$INVOICE_ID\",
    \"customer_id\": \"$CUSTOMER_ID\",
    \"amount\": 219.98
  }")
echo "$PAYMENT_RESPONSE" | python -m json.tool
PAYMENT_ID=$(echo "$PAYMENT_RESPONSE" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Payment ID: $PAYMENT_ID"
echo ""

# Step 8: Process payment
echo "Step 8: Processing payment..."
PROCESS_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/payments/$PAYMENT_ID/process")
echo "$PROCESS_RESPONSE" | python -m json.tool
echo ""

# Step 9: Verify payment (Workflow Step 5)
echo "Step 9: Verifying payment..."
VERIFY_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/payments/$PAYMENT_ID/verify")
echo "$VERIFY_RESPONSE" | python -m json.tool
echo ""

# Step 10: Ship order (Workflow Step 6)
echo "Step 10: Shipping order..."
SHIP_RESPONSE=$(curl -s -X PATCH "$BASE_URL/api/v1/orders/$ORDER_ID/ship?tracking_number=TRACK-123")
echo "$SHIP_RESPONSE" | python -m json.tool
echo ""

# Step 11: Close order (Workflow Step 7)
echo "Step 11: Closing order..."
CLOSE_RESPONSE=$(curl -s -X PATCH "$BASE_URL/api/v1/orders/$ORDER_ID/close")
echo "$CLOSE_RESPONSE" | python -m json.tool
echo ""

# Final verification
echo "=== Final NFR Verification ==="
echo ""
curl -s "$BASE_URL/api/v1/health/nfr-verification" | python -m json.tool
echo ""

echo "=== Workflow Complete ==="
