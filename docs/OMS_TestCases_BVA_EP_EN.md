# OMS Test Case Suite (BVA + EP)

## README

OMS - Test Case Suite (BVA + EP) - Derived from Domain Model Field Constraint Table

Source: Field Constraint Table (Domain Model constraints for BVA/EP test design)

- **Column**: Meaning
- **Test Case ID**: Format: TC_<ENTITY>_<ATTRIBUTE>_<SEQ>
- **Entity**: Domain entity under test (Customer, Product, Order, Payment, Invoice)
- **Attribute**: Field under test
- **Test Basis**: Design technique used: BVA (Boundary Value Analysis) or EP (Equivalence Partitioning)
- **Equivalence Class / Boundary**: For EP: class label, e.g. EC-Valid-1, EC-Invalid-1 (Empty), EC-Invalid-2 (Wrong Type). For BVA: boundary label, e.g. BC-Min-1, BC-Min, BC-Max, BC-Max+1
- **Test Objective**: Short description of what the test case verifies
- **Input Value**: Concrete value supplied to the attribute under test
- **Preconditions (other fields assumed valid)**: Other request fields assumed valid so this test isolates the attribute under test
- **Expected Output**: Expected business-level outcome
- **Expected HTTP Status**: Expected HTTP status code: 2xx for valid classes, 4xx for invalid classes (exact code to be confirmed against the API error contract)
- **Priority**: High / Medium / Low, carried over from the Field Constraint Table
- **Result**: Leave blank; fill Pass/Fail during execution
- **Remarks**: Additional notes, e.g. FK dependency, cross-field rule, semantic rule

BVA/EP Convention used in this workbook:
- EP: each attribute is partitioned into valid and invalid equivalence classes. Each class is represented by exactly one representative test case (per standard EP practice).
  Class labels: EC-Valid-<n> for valid partitions, EC-Invalid-<n> (<reason>) for invalid partitions, e.g. EC-Invalid-1 (Empty), EC-Invalid-2 (Wrong Format), EC-Invalid-3 (Unsupported Value).
- BVA: applied only to attributes with a numeric or length boundary (min/max). Exactly 4 boundary points are tested per bounded attribute: BC-Min-1 (invalid), BC-Min (valid), BC-Max (valid), BC-Max+1 (invalid).
- BVA is NOT applied to enum, UUID/FK, or free-form unbounded fields; these are covered by EP only, consistent with standard test design theory.
- Fields with cross-entity or workflow dependencies (computed totals, payment amount vs invoice amount, order status transitions) are flagged in Remarks; full coverage for these belongs to a separate Business Rule / State Transition table (Table B), not in scope of this file.

Important notes:
- FK test cases (customerRef, productRef, orderRef, invoiceRef...) require seed data prior to execution (one valid existing record + one syntactically valid but non-existent UUID).
- Cross-field / business rule test cases (computed totalAmount, payment.amount == invoice.totalAmount, state transitions) belong to Table B (Business Rule / State Transition table), not generated in this file.
- Date fields (dd/MM/yyyy) have two distinct invalid classes: wrong format (regex mismatch) and wrong semantic (non-existent calendar date, e.g. 31/02) - kept as separate test cases.
- Expected HTTP Status values are REST-convention defaults and must be reconciled with the actual API error contract once the backend is implemented.

## Summary

| Test Case Summary |  |  |  |  |  |  |
|---|---|---|---|---|---|---|
| Entity | Total Test Cases | BVA | EP | High Priority | Medium Priority | Low Priority |
| Customer | 50 | 20 | 30 | 28 | 13 | 9 |
| Product | 25 | 9 | 16 | 18 | 7 | 0 |
| Order | 28 | 8 | 20 | 23 | 5 | 0 |
| Payment | 18 | 0 | 18 | 13 | 5 | 0 |
| Invoice | 26 | 9 | 17 | 10 | 16 | 0 |
| TOTAL |  |  |  |  |  |  |

## Customer

| Test Case ID | Entity | Attribute | Test Basis | Equivalence Class / Boundary | Test Objective | Input Value | Preconditions (other fields assumed valid) | Expected Output | Expected HTTP Status | Priority | Result | Remarks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_CUS_ID_01 | Customer | id | EP | EC-Valid-1 | Retrieve customer using a well-formed, existing UUID | <seed: existing customer id> | N/A - id is tested in isolation | Returns the matching customer record | 200 | High |  |  |
| TC_CUS_ID_02 | Customer | id | EP | EC-Invalid-1 (Not Found) | Well-formed UUID that does not exist | 3fa85f64-5717-4562-b3fc-2c963f66afa6 | N/A - id is tested in isolation | Customer not found | 404 | High |  |  |
| TC_CUS_ID_03 | Customer | id | EP | EC-Invalid-2 (Wrong Format) | Malformed UUID string | not-a-uuid-123 | N/A - id is tested in isolation | Rejected due to invalid format | 400 | High |  |  |
| TC_CUS_ID_04 | Customer | id | EP | EC-Invalid-3 (Empty) | Empty/null id |  | N/A - id is tested in isolation | Rejected - id is required | 405 | High |  |  |
| TC_CUS_NAME_01 | Customer | name | BVA | BC-Min-1 | Length one below minimum (1 char) | A | address/phone/bankingDetails/role valid | Rejected - below minimum length (< 2) | 400 | High |  |  |
| TC_CUS_NAME_02 | Customer | name | BVA | BC-Min | Length at minimum (2 chars) | An | address/phone/bankingDetails/role valid | Customer created successfully | 201 | High |  |  |
| TC_CUS_NAME_03 | Customer | name | BVA | BC-Max | Length at maximum (100 chars) | AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA | address/phone/bankingDetails/role valid | Customer created successfully | 201 | High |  |  |
| TC_CUS_NAME_04 | Customer | name | BVA | BC-Max+1 | Length one above maximum (101 chars) | AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA | address/phone/bankingDetails/role valid | Rejected - exceeds maximum length (> 100) | 400 | High |  |  |
| TC_CUS_NAME_05 | Customer | name | EP | EC-Valid-1 | Ordinary name with space | Nguyen Van A | address/phone/bankingDetails/role valid | Customer created successfully | 201 | High |  |  |
| TC_CUS_NAME_06 | Customer | name | EP | EC-Valid-2 | Name containing hyphen/apostrophe | Jean-Luc O'Brien | address/phone/bankingDetails/role valid | Customer created successfully | 201 | High |  |  |
| TC_CUS_NAME_07 | Customer | name | EP | EC-Invalid-1 (Empty) | Empty string |  | address/phone/bankingDetails/role valid | Rejected - name is required | 400 | High |  |  |
| TC_CUS_NAME_08 | Customer | name | EP | EC-Invalid-2 (Digits Only) | Numeric-only string | 12345 | address/phone/bankingDetails/role valid | Rejected - does not match name pattern | 400 | High |  |  |
| TC_CUS_NAME_09 | Customer | name | EP | EC-Invalid-3 (Symbols Only) | Special characters only | @#$%^& | address/phone/bankingDetails/role valid | Rejected - does not match name pattern | 400 | High |  |  |
| TC_CUS_NAME_10 | Customer | name | EP | EC-Invalid-4 (Whitespace Only) | Whitespace-only string |       | address/phone/bankingDetails/role valid | Rejected - blank after trim | 400 | High |  |  |
| TC_CUS_ADDRESS_01 | Customer | address | BVA | BC-Min-1 | Length one below minimum (4 chars) | 12 A | name/phone/bankingDetails/role valid | Rejected - below minimum length (< 5) | 400 | Medium |  |  |
| TC_CUS_ADDRESS_02 | Customer | address | BVA | BC-Min | Length at minimum (5 chars) | 12345 | name/phone/bankingDetails/role valid | Customer created successfully | 201 | Medium |  |  |
| TC_CUS_ADDRESS_03 | Customer | address | BVA | BC-Max | Length at maximum (255 chars) | AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA | name/phone/bankingDetails/role valid | Customer created successfully | 201 | Medium |  |  |
| TC_CUS_ADDRESS_04 | Customer | address | BVA | BC-Max+1 | Length one above maximum (256 chars) | AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA | name/phone/bankingDetails/role valid | Rejected - exceeds maximum length (> 255) | 400 | Medium |  |  |
| TC_CUS_ADDRESS_05 | Customer | address | EP | EC-Invalid-1 (Empty) | Empty string |  | name/phone/bankingDetails/role valid | Rejected - address is required | 400 | Medium |  |  |
| TC_CUS_ADDRESS_06 | Customer | address | EP | EC-Invalid-2 (Whitespace Only) | Whitespace-only string |          | name/phone/bankingDetails/role valid | Rejected - blank after trim | 400 | Medium |  |  |
| TC_CUS_ADDRESS_07 | Customer | address | EP | EC-Valid-1 | Ordinary full address | 123 Nguyen Trai, Thanh Xuan, Hanoi | name/phone/bankingDetails/role valid | Customer created successfully | 201 | Medium |  |  |
| TC_CUS_PHONE_01 | Customer | phone | BVA | BC-Min-1 | Digit count one below minimum (7 digits) | +8412345 | name/address/bankingDetails/role valid | Rejected - below minimum length | 400 | High |  |  |
| TC_CUS_PHONE_02 | Customer | phone | BVA | BC-Min | Digit count at minimum (8 digits) | +84912345 | name/address/bankingDetails/role valid | Customer created successfully | 201 | High |  |  |
| TC_CUS_PHONE_03 | Customer | phone | BVA | BC-Max | Digit count at maximum (15 digits) | +841234567890123 | name/address/bankingDetails/role valid | Customer created successfully | 201 | High |  |  |
| TC_CUS_PHONE_04 | Customer | phone | BVA | BC-Max+1 | Digit count one above maximum (16 digits) | +8412345678901234 | name/address/bankingDetails/role valid | Rejected - exceeds maximum length | 400 | High |  |  |
| TC_CUS_PHONE_05 | Customer | phone | EP | EC-Valid-1 | E.164 without leading + | 84912345678 | name/address/bankingDetails/role valid | Customer created successfully | 201 | High |  |  |
| TC_CUS_PHONE_06 | Customer | phone | EP | EC-Invalid-1 (Contains Letters) | Alphanumeric mix | +849abc45678 | name/address/bankingDetails/role valid | Rejected - does not match pattern | 400 | High |  |  |
| TC_CUS_PHONE_07 | Customer | phone | EP | EC-Invalid-2 (Leading Zero) | Starts with 0 after country code | +8401234567 | name/address/bankingDetails/role valid | Rejected - violates semantic rule | 400 | High |  |  |
| TC_CUS_PHONE_08 | Customer | phone | EP | EC-Invalid-3 (Empty) | Empty/null |  | name/address/bankingDetails/role valid | Rejected - phone is required | 400 | High |  |  |
| TC_CUS_BANKACCTNU_01 | Customer | bankingDetails.accountNumber | BVA | BC-Min-1 | Length one below minimum (5 digits) | 12345 | name/address/phone/bankName/role valid | Rejected - below minimum length (< 6) | 400 | Medium |  |  |
| TC_CUS_BANKACCTNU_02 | Customer | bankingDetails.accountNumber | BVA | BC-Min | Length at minimum (6 digits) | 123456 | name/address/phone/bankName/role valid | Customer created successfully | 201 | Medium |  |  |
| TC_CUS_BANKACCTNU_03 | Customer | bankingDetails.accountNumber | BVA | BC-Max | Length at maximum (20 digits) | 11111111111111111111 | name/address/phone/bankName/role valid | Customer created successfully | 201 | Medium |  |  |
| TC_CUS_BANKACCTNU_04 | Customer | bankingDetails.accountNumber | BVA | BC-Max+1 | Length one above maximum (21 digits) | 111111111111111111111 | name/address/phone/bankName/role valid | Rejected - exceeds maximum length (> 20) | 400 | Medium |  |  |
| TC_CUS_BANKACCTNU_05 | Customer | bankingDetails.accountNumber | EP | EC-Invalid-1 (Contains Letters) | Alphanumeric mix | 12ab56 | name/address/phone/bankName/role valid | Rejected - must be numeric only | 400 | Medium |  |  |
| TC_CUS_BANKACCTNU_06 | Customer | bankingDetails.accountNumber | EP | EC-Invalid-2 (Empty) | Empty string |  | name/address/phone/bankName/role valid | Rejected - accountNumber is required | 400 | Medium |  |  |
| TC_CUS_BANKNAME_01 | Customer | bankingDetails.bankName | BVA | BC-Min-1 | Length one below minimum (1 char) | A | name/address/phone/accountNumber/role valid | Rejected - below minimum length (< 2) | 400 | Low |  |  |
| TC_CUS_BANKNAME_02 | Customer | bankingDetails.bankName | BVA | BC-Min | Length at minimum (2 chars) | VP | name/address/phone/accountNumber/role valid | Customer created successfully | 201 | Low |  |  |
| TC_CUS_BANKNAME_03 | Customer | bankingDetails.bankName | BVA | BC-Max | Length at maximum (100 chars) | AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA | name/address/phone/accountNumber/role valid | Customer created successfully | 201 | Low |  |  |
| TC_CUS_BANKNAME_04 | Customer | bankingDetails.bankName | BVA | BC-Max+1 | Length one above maximum (101 chars) | AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA | name/address/phone/accountNumber/role valid | Rejected - exceeds maximum length (> 100) | 400 | Low |  |  |
| TC_CUS_BANKNAME_05 | Customer | bankingDetails.bankName | EP | EC-Invalid-1 (Empty) | Empty string |  | name/address/phone/accountNumber/role valid | Rejected - bankName is required | 400 | Low |  |  |
| TC_CUS_BANKNAME_06 | Customer | bankingDetails.bankName | EP | EC-Valid-1 | Realistic bank name | Vietcombank | name/address/phone/accountNumber/role valid | Customer created successfully | 201 | Low |  |  |
| TC_CUS_ROLE_01 | Customer | role | EP | EC-Valid-1 | Valid role - CUSTOMER | CUSTOMER | name/address/phone/bankingDetails valid | Customer created with role CUSTOMER | 201 | High |  |  |
| TC_CUS_ROLE_02 | Customer | role | EP | EC-Valid-2 | Valid role - ORDER_STAFF | ORDER_STAFF | name/address/phone/bankingDetails valid | Customer created with role ORDER_STAFF | 201 | High |  |  |
| TC_CUS_ROLE_03 | Customer | role | EP | EC-Valid-3 | Valid role - ACCOUNTANT | ACCOUNTANT | name/address/phone/bankingDetails valid | Customer created with role ACCOUNTANT | 201 | High |  |  |
| TC_CUS_ROLE_04 | Customer | role | EP | EC-Invalid-1 (Unknown Value) | Value not part of enum | MANAGER | name/address/phone/bankingDetails valid | Rejected - invalid enum value | 400 | High |  |  |
| TC_CUS_ROLE_05 | Customer | role | EP | EC-Invalid-2 (Wrong Case) | Lowercase value | customer | name/address/phone/bankingDetails valid | Rejected - invalid enum value (case-sensitive) | 400 | High |  |  |
| TC_CUS_ROLE_06 | Customer | role | EP | EC-Invalid-3 (Empty) | Empty/null |  | name/address/phone/bankingDetails valid | Rejected - role is required | 400 | High |  |  |
| TC_CUS_ORDERHIST_01 | Customer | orderHistory | EP | EC-Valid-1 | Empty array (newly created customer, no orders yet) | [] | name/address/phone/bankingDetails/role valid | Rejected - orderHistory is read-only/server-derived, extra field not permitted | 400 | Low |  | Field is read-only / server-derived |
| TC_CUS_ORDERHIST_02 | Customer | orderHistory | EP | EC-Invalid-1 (Malformed Item) | Array containing a malformed UUID | ["not-a-uuid"] | name/address/phone/bankingDetails/role valid | Rejected, or field ignored (read-only, not client-settable) | 400 | Low |  | Field is read-only / server-derived |
| TC_CUS_ORDERHIST_03 | Customer | orderHistory | EP | EC-Invalid-2 (Client-Supplied Read-Only Field) | Client attempts to set a read-only field | ["3fa85f64-..."] | name/address/phone/bankingDetails/role valid | System ignores or rejects client-supplied value | 400 | Low |  | Field is read-only / server-derived |

## Product

| Test Case ID | Entity | Attribute | Test Basis | Equivalence Class / Boundary | Test Objective | Input Value | Preconditions (other fields assumed valid) | Expected Output | Expected HTTP Status | Priority | Result | Remarks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_PRO_ID_01 | Product | id | EP | EC-Valid-1 | Retrieve product using a well-formed, existing UUID | <seed: existing product id> | N/A | Returns the matching product record | 200 | High |  |  |
| TC_PRO_ID_02 | Product | id | EP | EC-Invalid-1 (Not Found) | Well-formed UUID that does not exist | 3fa85f64-5717-4562-b3fc-2c963f66afa6 | N/A | Product not found | 404 | High |  |  |
| TC_PRO_ID_03 | Product | id | EP | EC-Invalid-2 (Wrong Format) | Malformed UUID string | prod-123 | N/A | Rejected due to invalid format | 400 | High |  |  |
| TC_PRO_DESCRIPTIO_01 | Product | description | BVA | BC-Min-1 | Length one below minimum (2 chars) | AB | price.amount/price.currency valid | Rejected - below minimum length (< 3) | 400 | Medium |  |  |
| TC_PRO_DESCRIPTIO_02 | Product | description | BVA | BC-Min | Length at minimum (3 chars) | USB | price.amount/price.currency valid | Product created successfully | 201 | Medium |  |  |
| TC_PRO_DESCRIPTIO_03 | Product | description | BVA | BC-Max | Length at maximum (500 chars) | AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA | price.amount/price.currency valid | Product created successfully | 201 | Medium |  |  |
| TC_PRO_DESCRIPTIO_04 | Product | description | BVA | BC-Max+1 | Length one above maximum (501 chars) | AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA | price.amount/price.currency valid | Rejected - exceeds maximum length (> 500) | 400 | Medium |  |  |
| TC_PRO_DESCRIPTIO_05 | Product | description | EP | EC-Invalid-1 (Empty) | Empty string |  | price.amount/price.currency valid | Rejected - description is required | 400 | Medium |  |  |
| TC_PRO_DESCRIPTIO_06 | Product | description | EP | EC-Invalid-2 (Whitespace Only) | Whitespace-only string |       | price.amount/price.currency valid | Rejected - blank after trim | 400 | Medium |  |  |
| TC_PRO_DESCRIPTIO_07 | Product | description | EP | EC-Valid-1 | Ordinary product description | Logitech M185 Wireless Mouse | price.amount/price.currency valid | Product created successfully | 201 | Medium |  |  |
| TC_PRO_PRICEAMT_01 | Product | price.amount | BVA | BC-Min-1 | Value below minimum boundary (0.00) | 0.00 | description/price.currency valid | Rejected - must be greater than 0 | 400 | High |  |  |
| TC_PRO_PRICEAMT_02 | Product | price.amount | BVA | BC-Min | Value at minimum (0.01) | 0.01 | description/price.currency valid | Product created successfully | 201 | High |  |  |
| TC_PRO_PRICEAMT_03 | Product | price.amount | BVA | BC-Max | Value at maximum (999999.99) | 999999.99 | description/price.currency valid | Product created successfully | 201 | High |  |  |
| TC_PRO_PRICEAMT_04 | Product | price.amount | BVA | BC-Max+1 | Value above maximum (1000000.00) | 1000000.00 | description/price.currency valid | Rejected - exceeds maximum value | 400 | High |  |  |
| TC_PRO_PRICEAMT_05 | Product | price.amount | EP | EC-Invalid-1 (Negative) | Negative value | -10.00 | description/price.currency valid | Rejected - negative value not allowed | 400 | High |  |  |
| TC_PRO_PRICEAMT_06 | Product | price.amount | EP | EC-Invalid-2 (Wrong Decimal Precision) | More than 2 decimal places | 10.999 | description/price.currency valid | Rejected - invalid decimal format | 400 | High |  |  |
| TC_PRO_PRICEAMT_07 | Product | price.amount | EP | EC-Invalid-3 (Non-Numeric) | Non-numeric string | abc | description/price.currency valid | Rejected - invalid data type | 400 | High |  |  |
| TC_PRO_PRICEAMT_08 | Product | price.amount | EP | EC-Invalid-4 (Empty) | Empty/null |  | description/price.currency valid | Rejected - price.amount is required | 400 | High |  |  |
| TC_PRO_CURRENCY_01 | Product | price.currency | EP | EC-Valid-1 | Supported currency - USD | USD | description/price.amount valid | Product created successfully | 201 | High |  |  |
| TC_PRO_CURRENCY_02 | Product | price.currency | EP | EC-Valid-2 | Supported currency - VND | VND | description/price.amount valid | Product created successfully | 201 | High |  |  |
| TC_PRO_CURRENCY_03 | Product | price.currency | EP | EC-Valid-3 | Supported currency - EUR | EUR | description/price.amount valid | Product created successfully | 201 | High |  |  |
| TC_PRO_CURRENCY_04 | Product | price.currency | BVA | BC-Length-Mismatch | Length below fixed length (2 chars, also invalid code) | US | description/price.amount valid | Rejected - invalid length/not in supported list | 400 | High |  |  |
| TC_PRO_CURRENCY_05 | Product | price.currency | EP | EC-Invalid-1 (Unsupported Code) | Well-formed 3-letter code not in supported list | XYZ | description/price.amount valid | Rejected - unsupported currency | 400 | High |  |  |
| TC_PRO_CURRENCY_06 | Product | price.currency | EP | EC-Invalid-2 (Wrong Case) | Lowercase value | usd | description/price.amount valid | Rejected - does not match ^[A-Z]{3}$ | 400 | High |  |  |
| TC_PRO_CURRENCY_07 | Product | price.currency | EP | EC-Invalid-3 (Empty) | Empty/null |  | description/price.amount valid | Rejected - price.currency is required | 400 | High |  |  |

## Order

| Test Case ID | Entity | Attribute | Test Basis | Equivalence Class / Boundary | Test Objective | Input Value | Preconditions (other fields assumed valid) | Expected Output | Expected HTTP Status | Priority | Result | Remarks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_ORD_CUSTREF_01 | Order | customerRef | EP | EC-Valid-1 | Existing, valid customerRef | <seed: existing customer id> | lineItems valid (>=1 item) | Order created successfully | 201 | High |  |  |
| TC_ORD_CUSTREF_02 | Order | customerRef | EP | EC-Invalid-1 (Not Found) | Well-formed UUID that does not exist | 3fa85f64-5717-4562-b3fc-2c963f66afa6 | lineItems valid (>=1 item) | Rejected - customer not found | 404 | High |  |  |
| TC_ORD_CUSTREF_03 | Order | customerRef | EP | EC-Invalid-2 (Wrong Format) | Malformed UUID string | cust-1 | lineItems valid (>=1 item) | Rejected - invalid format | 400 | High |  |  |
| TC_ORD_CUSTREF_04 | Order | customerRef | EP | EC-Invalid-3 (Empty) | Empty/null |  | lineItems valid (>=1 item) | Rejected - customerRef is required | 400 | High |  |  |
| TC_ORD_LINEITEMS_01 | Order | lineItems | BVA | BC-Min-1 | Item count one below minimum (0 items) | [] | customerRef valid | Rejected - order must contain at least 1 item | 400 | High |  | Business rule to be confirmed |
| TC_ORD_LINEITEMS_02 | Order | lineItems | BVA | BC-Min | Item count at minimum (1 item) | [{productRef, quantity:1}] | customerRef valid | Order created successfully | 201 | High |  | Business rule to be confirmed |
| TC_ORD_LINEITEMS_03 | Order | lineItems | BVA | BC-Max | Item count at maximum (100 items) | [100 distinct productRef items] | customerRef valid | Order created successfully | 201 | High |  | Business rule to be confirmed |
| TC_ORD_LINEITEMS_04 | Order | lineItems | BVA | BC-Max+1 | Item count one above maximum (101 items) | [101 items] | customerRef valid | Rejected - exceeds maximum item count | 400 | High |  | Business rule to be confirmed |
| TC_ORD_LINEITEMS_05 | Order | lineItems | EP | EC-Invalid-1 (Non-Existent Product) | Item references a non-existent product | [{productRef: <not-exist-uuid>, quantity:1}] | customerRef valid | Rejected - product not found | 404 | High |  | Business rule to be confirmed |
| TC_ORD_LINEITEMS_06 | Order | lineItems | EP | EC-Invalid-2 (Missing) | lineItems null/missing entirely | null | customerRef valid | Rejected - lineItems is required | 400 | High |  | Business rule to be confirmed |
| TC_ORD_LINEITEMS_07 | Order | lineItems | EP | EC-Invalid-3 (Duplicate Product) | Two items reference the same productRef | [{productRef:P1,qty:1},{productRef:P1,qty:2}] | customerRef valid | Rejected | 400 | High |  | Business rule to be confirmed |
| TC_ORD_QTY_01 | Order | lineItems[].quantity | BVA | BC-Min-1 | Value one below minimum (0) | 0 | productRef valid, other order fields valid | Rejected - quantity must be >= 1 | 400 | High |  |  |
| TC_ORD_QTY_02 | Order | lineItems[].quantity | BVA | BC-Min | Value at minimum (1) | 1 | productRef valid, other order fields valid | Order created successfully | 201 | High |  |  |
| TC_ORD_QTY_03 | Order | lineItems[].quantity | BVA | BC-Max | Value at maximum (1000) | 1000 | productRef valid, other order fields valid | Order created successfully | 201 | High |  |  |
| TC_ORD_QTY_04 | Order | lineItems[].quantity | BVA | BC-Max+1 | Value one above maximum (1001) | 1001 | productRef valid, other order fields valid | Rejected - exceeds maximum quantity | 400 | High |  |  |
| TC_ORD_QTY_05 | Order | lineItems[].quantity | EP | EC-Invalid-1 (Negative) | Negative value | -5 | productRef valid, other order fields valid | Rejected - negative value not allowed | 400 | High |  |  |
| TC_ORD_QTY_06 | Order | lineItems[].quantity | EP | EC-Invalid-2 (Decimal) | Non-integer value | 1.5 | productRef valid, other order fields valid | Rejected - must be a whole number | 400 | High |  |  |
| TC_ORD_QTY_07 | Order | lineItems[].quantity | EP | EC-Invalid-3 (Non-Numeric) | Non-numeric value | abc | productRef valid, other order fields valid | Rejected - invalid data type | 400 | High |  |  |
| TC_ORD_UNITPRICE_01 | Order | lineItems[].unitPriceSnapshot | EP | EC-Valid-1 | Client omits price; server derives snapshot from current Product price | N/A - server-computed | productRef valid | Server snapshots current product price correctly | 201 | Medium |  | Field should be server-computed, not client-supplied |
| TC_ORD_UNITPRICE_02 | Order | lineItems[].unitPriceSnapshot | EP | EC-Invalid-1 (Tampered Value) | Client supplies a price different from current Product price | 0.01 (while Product is priced at 100.00) | productRef valid | Rejected | 400 | Medium |  | Field should be server-computed, not client-supplied |
| TC_ORD_TOTALAMT_01 | Order | totalAmount | EP | EC-Valid-1 | Server correctly computes total = sum(quantity * unitPrice) | N/A - server-computed | lineItems valid | Returned totalAmount matches computed sum | 201 | High |  | Server-computed field; see Table B |
| TC_ORD_TOTALAMT_02 | Order | totalAmount | EP | EC-Invalid-1 (Client-Supplied Mismatch) | Client supplies a totalAmount different from the computed value | 999999.99 (incorrect) | lineItems valid | Rejected | 400 | High |  | Server-computed field; see Table B |
| TC_ORD_STATUS_01 | Order | status | EP | EC-Valid-1 | Default status on creation is PLACED | PLACED | customerRef/lineItems valid | Order created with status PLACED | 201 | High |  | Full transition coverage in Table B |
| TC_ORD_STATUS_02 | Order | status | EP | EC-Invalid-1 (Bypasses Workflow) | Client sets status other than PLACED on creation | SHIPPED | customerRef/lineItems valid | Rejected - workflow cannot be bypassed | 400 | High |  | Full transition coverage in Table B |
| TC_ORD_STATUS_03 | Order | status | EP | EC-Invalid-2 (Unknown Value) | Value not part of enum | DONE | customerRef/lineItems valid | Rejected - invalid enum value | 400 | High |  | Full transition coverage in Table B |
| TC_ORD_INVREF_01 | Order | invoiceRef | EP | EC-Valid-1 | invoiceRef null prior to invoicing (e.g. PLACED/ACCEPTED) | null | order in correct state | Valid - invoice not yet created | 200 | Medium |  |  |
| TC_ORD_INVREF_02 | Order | invoiceRef | EP | EC-Valid-2 | invoiceRef valid after invoice creation | <seed: existing invoice id> | order in correct state | Valid - linked to invoice | 200 | Medium |  |  |
| TC_ORD_INVREF_03 | Order | invoiceRef | EP | EC-Invalid-1 (Not Found) | invoiceRef references a non-existent invoice | 3fa85f64-5717-4562-b3fc-2c963f66afa6 | order in correct state | Rejected - invoice not found | 404 | Medium |  |  |

## Payment

| Test Case ID | Entity | Attribute | Test Basis | Equivalence Class / Boundary | Test Objective | Input Value | Preconditions (other fields assumed valid) | Expected Output | Expected HTTP Status | Priority | Result | Remarks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_PAY_ORDERREF_01 | Payment | orderRef | EP | EC-Valid-1 | orderRef exists and order status is INVOICED | <seed: order status=INVOICED> | amount/method valid | Payment created successfully | 201 | High |  |  |
| TC_PAY_ORDERREF_02 | Payment | orderRef | EP | EC-Invalid-1 (Wrong State) | orderRef exists but order status is not payable (e.g. PLACED) | <seed: order status=PLACED> | amount/method valid | Rejected - order not in a payable state | 409 | High |  |  |
| TC_PAY_ORDERREF_03 | Payment | orderRef | EP | EC-Invalid-2 (Not Found) | orderRef does not exist | 3fa85f64-5717-4562-b3fc-2c963f66afa6 | amount/method valid | Rejected - order not found | 404 | High |  |  |
| TC_PAY_ORDERREF_04 | Payment | orderRef | EP | EC-Invalid-3 (Wrong Format) | Malformed UUID string | order-1 | amount/method valid | Rejected - invalid format | 400 | High |  |  |
| TC_PAY_AMOUNT_01 | Payment | amount | EP | EC-Valid-1 | amount exactly equals invoice.totalAmount | <seed: equal to invoice.totalAmount> | orderRef/method valid, order already invoiced | Payment accepted | 201 | High |  | Exact-match rule; partial payment policy to be confirmed |
| TC_PAY_AMOUNT_02 | Payment | amount | EP | EC-Invalid-1 (Underpayment) | amount less than invoice.totalAmount | invoice.totalAmount - 0.01 | orderRef/method valid, order already invoiced | Rejected - underpayment not accepted | 409 | High |  | Exact-match rule; partial payment policy to be confirmed |
| TC_PAY_AMOUNT_03 | Payment | amount | EP | EC-Invalid-2 (Overpayment) | amount greater than invoice.totalAmount | invoice.totalAmount + 0.01 | orderRef/method valid, order already invoiced | Rejected - overpayment not accepted | 409 | High |  | Exact-match rule; partial payment policy to be confirmed |
| TC_PAY_AMOUNT_04 | Payment | amount | EP | EC-Invalid-3 (Zero) | amount equal to zero | 0.00 | orderRef/method valid, order already invoiced | Rejected - must be greater than 0 | 400 | High |  | Exact-match rule; partial payment policy to be confirmed |
| TC_PAY_AMOUNT_05 | Payment | amount | EP | EC-Invalid-4 (Negative) | Negative value | -50.00 | orderRef/method valid, order already invoiced | Rejected - negative value not allowed | 400 | High |  | Exact-match rule; partial payment policy to be confirmed |
| TC_PAY_AMOUNT_06 | Payment | amount | EP | EC-Invalid-5 (Empty) | Empty/null |  | orderRef/method valid, order already invoiced | Rejected - amount is required | 400 | High |  | Exact-match rule; partial payment policy to be confirmed |
| TC_PAY_STATUS_01 | Payment | status | EP | EC-Valid-1 | Default status on creation is PENDING | PENDING | orderRef/amount/method valid | Payment created with status PENDING | 201 | High |  |  |
| TC_PAY_STATUS_02 | Payment | status | EP | EC-Invalid-1 (Bypasses Workflow) | Client sets status to VERIFIED on creation (bypassing accountant verification) | VERIFIED | orderRef/amount/method valid | Rejected - cannot self-verify | 400 | High |  |  |
| TC_PAY_STATUS_03 | Payment | status | EP | EC-Invalid-2 (Unknown Value) | Value not part of enum | DONE | orderRef/amount/method valid | Rejected - invalid enum value | 400 | High |  |  |
| TC_PAY_METHOD_01 | Payment | method | EP | EC-Valid-1 | Valid method - CREDIT_CARD | CREDIT_CARD | orderRef/amount valid | Payment created successfully | 201 | Medium |  |  |
| TC_PAY_METHOD_02 | Payment | method | EP | EC-Valid-2 | Valid method - BANK_TRANSFER | BANK_TRANSFER | orderRef/amount valid | Payment created successfully | 201 | Medium |  |  |
| TC_PAY_METHOD_03 | Payment | method | EP | EC-Valid-3 | Valid method - E_WALLET | E_WALLET | orderRef/amount valid | Payment created successfully | 201 | Medium |  |  |
| TC_PAY_METHOD_04 | Payment | method | EP | EC-Invalid-1 (Unknown Value) | Value not part of enum | CASH | orderRef/amount valid | Rejected - invalid enum value | 400 | Medium |  |  |
| TC_PAY_METHOD_05 | Payment | method | EP | EC-Invalid-2 (Empty) | Empty/null |  | orderRef/amount valid | Rejected - method is required | 400 | Medium |  |  |

## Invoice

| Test Case ID | Entity | Attribute | Test Basis | Equivalence Class / Boundary | Test Objective | Input Value | Preconditions (other fields assumed valid) | Expected Output | Expected HTTP Status | Priority | Result | Remarks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_INV_ORDERREF_01 | Invoice | orderRef | EP | EC-Valid-1 | orderRef exists and order status is ACCEPTED | <seed: order status=ACCEPTED> | billingInfo/issueDate/dueDate valid | Invoice created successfully | 201 | High |  |  |
| TC_INV_ORDERREF_02 | Invoice | orderRef | EP | EC-Invalid-1 (Wrong State) | orderRef exists but order status is not ACCEPTED (e.g. PLACED) | <seed: order status=PLACED> | billingInfo/issueDate/dueDate valid | Rejected - order not yet accepted | 409 | High |  |  |
| TC_INV_ORDERREF_03 | Invoice | orderRef | EP | EC-Invalid-2 (Not Found) | orderRef does not exist | 3fa85f64-5717-4562-b3fc-2c963f66afa6 | billingInfo/issueDate/dueDate valid | Rejected - order not found | 404 | High |  |  |
| TC_INV_ORDERREF_04 | Invoice | orderRef | EP | EC-Invalid-3 (Wrong Format) | Malformed UUID string | order-1 | amount/method valid | Rejected - invalid format | 400 | High |  |  |
| TC_INV_BILLNAME_01 | Invoice | billingInfo.name | BVA | BC-Min-1 | Length one below minimum (1 char) | A | orderRef valid, other fields valid | Rejected - below minimum length | 400 | Medium |  | Snapshot of Customer.name |
| TC_INV_BILLNAME_02 | Invoice | billingInfo.name | BVA | BC-Min | Length at minimum (2 chars) | An | orderRef valid, other fields valid | Rejected - billingInfo is read-only/server-derived, extra field not permitted | 400 | Medium |  | Snapshot of Customer.name |
| TC_INV_BILLNAME_03 | Invoice | billingInfo.name | BVA | BC-Max | Length at maximum (100 chars) | AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA | orderRef valid, other fields valid | Rejected - billingInfo is read-only/server-derived, extra field not permitted | 400 | Medium |  | Snapshot of Customer.name |
| TC_INV_BILLNAME_04 | Invoice | billingInfo.name | BVA | BC-Max+1 | Length one above maximum (101 chars) | AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA | orderRef valid, other fields valid | Rejected - exceeds maximum length | 400 | Medium |  | Snapshot of Customer.name |
| TC_INV_TOTALAMT_01 | Invoice | totalAmount | EP | EC-Valid-1 | Server-computed totalAmount equals Order.totalAmount | N/A - server-computed | orderRef valid | totalAmount matches order.totalAmount | 201 | High |  | Server-computed field |
| TC_INV_TOTALAMT_02 | Invoice | totalAmount | EP | EC-Invalid-1 (Client-Supplied Mismatch) | Client supplies a totalAmount different from order.totalAmount | 0.01 (incorrect) | orderRef valid | Rejected | 400 | High |  | Server-computed field |
| TC_INV_TOTALAMT_03 | Invoice | totalAmount | BVA | BC-Min-1 | Value at zero boundary | 0.00 | orderRef valid | Rejected - must be greater than 0 | 400 | High |  | Server-computed field |
| TC_INV_ISSUEDATE_01 | Invoice | issueDate | EP | EC-Valid-1 | Valid date in dd/mm/yyyy format | 23/07/2026 | orderRef valid | Invoice created successfully | 201 | Medium |  | Format error vs semantic error kept separate |
| TC_INV_ISSUEDATE_02 | Invoice | issueDate | EP | EC-Invalid-1 (Wrong Separator) | Uses hyphen instead of slash | 23-07-2026 | orderRef valid | Rejected - format regex mismatch | 400 | Medium |  | Format error vs semantic error kept separate |
| TC_INV_ISSUEDATE_03 | Invoice | issueDate | EP | EC-Invalid-2 (Wrong Order) | yyyy/mm/dd order | 2026/07/23 | orderRef valid | Rejected - format regex mismatch | 400 | Medium |  | Format error vs semantic error kept separate |
| TC_INV_ISSUEDATE_04 | Invoice | issueDate | EP | EC-Invalid-3 (Non-Existent Date) | Well-formed but calendar-invalid date | 31/02/2026 | orderRef valid | Rejected - February does not have 31 days | 400 | Medium |  | Format error vs semantic error kept separate |
| TC_INV_ISSUEDATE_05 | Invoice | issueDate | EP | EC-Invalid-4 (Non-Existent Date) | Well-formed but calendar-invalid date | 30/02/2026 | orderRef valid | Rejected - February does not have 30 days | 400 | Medium |  | Format error vs semantic error kept separate |
| TC_INV_ISSUEDATE_06 | Invoice | issueDate | BVA | BC-Month-Min-1 | Month value below minimum (0) | 23/00/2026 | orderRef valid | Rejected - invalid month | 400 | Medium |  | Format error vs semantic error kept separate |
| TC_INV_ISSUEDATE_07 | Invoice | issueDate | BVA | BC-Month-Max+1 | Month value above maximum (13) | 23/13/2026 | orderRef valid | Rejected - invalid month | 400 | Medium |  | Format error vs semantic error kept separate |
| TC_INV_DUEDATE_01 | Invoice | dueDate | EP | EC-Valid-1 | dueDate = issueDate + 7 days (default) | 30/07/2026 (issueDate=23/07/2026) | orderRef/issueDate valid | Invoice created with default due date | 201 | Medium |  | Depends on issueDate |
| TC_INV_DUEDATE_02 | Invoice | dueDate | BVA | BC-Equal-Min | dueDate equals issueDate (0-day term, boundary equality) | 23/07/2026 (issueDate=23/07/2026) | orderRef/issueDate valid | Valid - accepted since dueDate >= issueDate | 201 | Medium |  | Depends on issueDate |
| TC_INV_DUEDATE_03 | Invoice | dueDate | BVA | BC-Min-1 | dueDate one day before issueDate | 22/07/2026 (issueDate=23/07/2026) | orderRef/issueDate valid | Rejected - dueDate cannot precede issueDate | 400 | Medium |  | Depends on issueDate |
| TC_INV_DUEDATE_04 | Invoice | dueDate | EP | EC-Invalid-1 (Wrong Format) | ISO format instead of dd/mm/yyyy | 2026-07-30 | orderRef/issueDate valid | Rejected - format regex mismatch | 400 | Medium |  | Depends on issueDate |
| TC_INV_DUEDATE_05 | Invoice | dueDate | EP | EC-Invalid-2 (Non-Existent Date) | Well-formed but calendar-invalid date | 31/04/2026 | orderRef/issueDate valid | Rejected - April does not have 31 days | 400 | Medium |  | Depends on issueDate |
| TC_INV_STATUS_01 | Invoice | status | EP | EC-Valid-1 | Default status on creation is ISSUED | ISSUED | orderRef/billingInfo/issueDate/dueDate valid | Invoice created with status ISSUED | 201 | High |  | Full transition coverage in Table B |
| TC_INV_STATUS_02 | Invoice | status | EP | EC-Invalid-1 (Bypasses Workflow) | Client sets status other than ISSUED on creation | PAID | orderRef/billingInfo/issueDate/dueDate valid | Rejected - workflow cannot be bypassed | 400 | High |  | Full transition coverage in Table B |
| TC_INV_STATUS_03 | Invoice | status | EP | EC-Invalid-2 (Unknown Value) | Value not part of enum | DRAFT | orderRef/billingInfo/issueDate/dueDate valid | Rejected - invalid enum value | 400 | High |  | Full transition coverage in Table B |
