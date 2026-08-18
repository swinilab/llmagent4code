"""
Validation utilities for field constraints
Implements all validation rules from the Field Constraint Table
"""
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional, Tuple
from uuid import UUID
from dateutil import parser as date_parser


# Regex patterns from Field Constraint Table
# Note: Using simplified patterns compatible with Python re module
# \p{L} replaced with Unicode letter ranges
PATTERNS = {
    "customer_name": re.compile(r"^[a-zA-Z\u00C0-\u024F .'\-]+$"),  # Letters, spaces, apostrophes, hyphens
    "customer_address": re.compile(r".{5,255}", re.DOTALL),
    "customer_phone": re.compile(r"^\+?[1-9]\d{7,14}$"),
    "account_number": re.compile(r"^\d{6,20}$"),
    "bank_name": re.compile(r"^[a-zA-Z0-9\u00C0-\u024F .&\-]+$"),  # Alphanumeric, spaces, symbols
    "product_description": re.compile(r".{3,500}", re.DOTALL),
    "price_amount": re.compile(r"^\d{1,6}\.\d{2}$"),
    "currency": re.compile(r"^[A-Z]{3}$"),
    "uuid": re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE),
    "quantity": re.compile(r"^\d+$"),
    "total_amount": re.compile(r"^\d{1,8}\.\d{2}$"),
    "date_ddmmyyyy": re.compile(r"^\d{2}/\d{2}/\d{4}$"),
}

# Allowed values for enums
ALLOWED_CUSTOMER_ROLES = {"CUSTOMER", "ORDER_STAFF", "ACCOUNTANT"}
ALLOWED_ORDER_STATUSES = {"PLACED", "ACCEPTED", "INVOICED", "PAID", "VERIFIED", "SHIPPED", "CLOSED", "CANCELLED"}
ALLOWED_PAYMENT_STATUSES = {"PENDING", "VERIFIED", "REJECTED"}
ALLOWED_PAYMENT_METHODS = {"CREDIT_CARD", "BANK_TRANSFER", "E_WALLET"}
ALLOWED_INVOICE_STATUSES = {"ISSUED", "PAID", "OVERDUE", "CANCELLED"}
SUPPORTED_CURRENCIES = {"USD", "VND", "EUR"}


def validate_uuid(value: Any) -> Tuple[bool, Optional[str]]:
    """Validate UUID format"""
    if not isinstance(value, str):
        return False, "Must be a string"
    if not PATTERNS["uuid"].match(value):
        return False, "Invalid UUID format"
    try:
        UUID(value, version=4)
        return True, None
    except ValueError:
        return False, "Invalid UUIDv4"


def validate_string_length(value: Any, min_len: int, max_len: int, field_name: str) -> Tuple[bool, Optional[str]]:
    """Validate string length"""
    if not isinstance(value, str):
        return False, f"{field_name} must be a string"
    if len(value) < min_len or len(value) > max_len:
        return False, f"{field_name} length must be between {min_len} and {max_len}"
    return True, None


def validate_not_blank(value: str, field_name: str) -> Tuple[bool, Optional[str]]:
    """Validate string is not blank or whitespace-only"""
    if not value or not value.strip():
        return False, f"{field_name} must not be blank"
    return True, None


def validate_customer_name(value: Any) -> Tuple[bool, Optional[str]]:
    """Validate customer name"""
    if not isinstance(value, str):
        return False, "Name must be a string"
    valid, err = validate_not_blank(value, "Name")
    if not valid:
        return valid, err
    valid, err = validate_string_length(value, 2, 100, "Name")
    if not valid:
        return valid, err
    if not PATTERNS["customer_name"].match(value):
        return False, "Name contains invalid characters"
    return True, None


def validate_customer_address(value: Any) -> Tuple[bool, Optional[str]]:
    """Validate customer address"""
    if not isinstance(value, str):
        return False, "Address must be a string"
    valid, err = validate_not_blank(value, "Address")
    if not valid:
        return valid, err
    valid, err = validate_string_length(value, 5, 255, "Address")
    if not valid:
        return valid, err
    return True, None


def validate_customer_phone(value: Any) -> Tuple[bool, Optional[str]]:
    """Validate customer phone (E.164 format)"""
    if not isinstance(value, str):
        return False, "Phone must be a string"
    if not PATTERNS["customer_phone"].match(value):
        return False, "Phone must be in E.164 format (8-15 digits, optional + prefix)"
    # Check doesn't start with 0 after country code
    digits_only = re.sub(r"\D", "", value)
    if len(digits_only) >= 2 and digits_only[1] == '0':
        return False, "Phone must not start with 0 after country code"
    return True, None


def validate_account_number(value: Any) -> Tuple[bool, Optional[str]]:
    """Validate bank account number"""
    if not isinstance(value, str):
        return False, "Account number must be a string"
    if not PATTERNS["account_number"].match(value):
        return False, "Account number must be 6-20 digits"
    return True, None


def validate_bank_name(value: Any) -> Tuple[bool, Optional[str]]:
    """Validate bank name"""
    if not isinstance(value, str):
        return False, "Bank name must be a string"
    valid, err = validate_string_length(value, 2, 100, "Bank name")
    if not valid:
        return valid, err
    if not PATTERNS["bank_name"].match(value):
        return False, "Bank name contains invalid characters"
    return True, None


def validate_customer_role(value: Any) -> Tuple[bool, Optional[str]]:
    """Validate customer role"""
    if value not in ALLOWED_CUSTOMER_ROLES:
        return False, f"Role must be one of: {', '.join(ALLOWED_CUSTOMER_ROLES)}"
    return True, None


def validate_product_description(value: Any) -> Tuple[bool, Optional[str]]:
    """Validate product description"""
    if not isinstance(value, str):
        return False, "Description must be a string"
    valid, err = validate_not_blank(value, "Description")
    if not valid:
        return valid, err
    valid, err = validate_string_length(value, 3, 500, "Description")
    if not valid:
        return valid, err
    return True, None


def validate_price_amount(value: Any) -> Tuple[bool, Optional[str]]:
    """Validate price amount (decimal with exactly 2 decimal places)"""
    if isinstance(value, (int, float)):
        value = f"{value:.2f}"
    if not isinstance(value, str):
        return False, "Price amount must be a string or number"
    if not PATTERNS["price_amount"].match(value):
        return False, "Price must have exactly 2 decimal places (e.g., 99.99)"
    try:
        decimal_val = Decimal(value)
        if decimal_val < Decimal("0.01") or decimal_val > Decimal("999999.99"):
            return False, "Price must be between 0.01 and 999999.99"
        return True, None
    except InvalidOperation:
        return False, "Invalid decimal value"


def validate_currency(value: Any) -> Tuple[bool, Optional[str]]:
    """Validate currency code"""
    if not isinstance(value, str):
        return False, "Currency must be a string"
    if not PATTERNS["currency"].match(value):
        return False, "Currency must be 3 uppercase letters"
    if value not in SUPPORTED_CURRENCIES:
        return False, f"Currency must be one of: {', '.join(SUPPORTED_CURRENCIES)}"
    return True, None


def validate_order_status(value: Any) -> Tuple[bool, Optional[str]]:
    """Validate order status"""
    if value not in ALLOWED_ORDER_STATUSES:
        return False, f"Status must be one of: {', '.join(ALLOWED_ORDER_STATUSES)}"
    return True, None


def validate_payment_status(value: Any) -> Tuple[bool, Optional[str]]:
    """Validate payment status"""
    if value not in ALLOWED_PAYMENT_STATUSES:
        return False, f"Status must be one of: {', '.join(ALLOWED_PAYMENT_STATUSES)}"
    return True, None


def validate_payment_method(value: Any) -> Tuple[bool, Optional[str]]:
    """Validate payment method"""
    if value not in ALLOWED_PAYMENT_METHODS:
        return False, f"Method must be one of: {', '.join(ALLOWED_PAYMENT_METHODS)}"
    return True, None


def validate_invoice_status(value: Any) -> Tuple[bool, Optional[str]]:
    """Validate invoice status"""
    if value not in ALLOWED_INVOICE_STATUSES:
        return False, f"Status must be one of: {', '.join(ALLOWED_INVOICE_STATUSES)}"
    return True, None


def validate_quantity(value: Any) -> Tuple[bool, Optional[str]]:
    """Validate quantity (integer 1-1000)"""
    if isinstance(value, str):
        if not PATTERNS["quantity"].match(value):
            return False, "Quantity must be a positive integer"
        value = int(value)
    if not isinstance(value, int):
        return False, "Quantity must be an integer"
    if value < 1 or value > 1000:
        return False, "Quantity must be between 1 and 1000"
    return True, None


def validate_total_amount(value: Any) -> Tuple[bool, Optional[str]]:
    """Validate total amount (decimal with exactly 2 decimal places)"""
    if isinstance(value, (int, float)):
        value = f"{value:.2f}"
    if not isinstance(value, str):
        return False, "Total amount must be a string or number"
    if not PATTERNS["total_amount"].match(value):
        return False, "Total amount must have exactly 2 decimal places"
    try:
        decimal_val = Decimal(value)
        if decimal_val < Decimal("0.01") or decimal_val > Decimal("99999999.99"):
            return False, "Total amount must be between 0.01 and 99999999.99"
        return True, None
    except InvalidOperation:
        return False, "Invalid decimal value"


def validate_date_ddmmyyyy(value: Any) -> Tuple[bool, Optional[str]]:
    """Validate date in dd/MM/yyyy format with calendar validity"""
    if not isinstance(value, str):
        return False, "Date must be a string"
    if not PATTERNS["date_ddmmyyyy"].match(value):
        return False, "Date must be in dd/MM/yyyy format"
    # Parse and validate it's a real calendar date
    try:
        day = int(value[0:2])
        month = int(value[3:5])
        year = int(value[6:10])
        # This will raise ValueError for invalid dates like 31/02/2026
        datetime(year, month, day)
        return True, None
    except ValueError:
        return False, "Invalid calendar date"


def validate_banking_details(value: Any) -> Tuple[bool, Optional[str]]:
    """Validate banking details object"""
    if not isinstance(value, dict):
        return False, "Banking details must be an object"
    if "accountNumber" not in value:
        return False, "Account number is required"
    if "bankName" not in value:
        return False, "Bank name is required"
    valid, err = validate_account_number(value["accountNumber"])
    if not valid:
        return False, f"accountNumber: {err}"
    valid, err = validate_bank_name(value["bankName"])
    if not valid:
        return False, f"bankName: {err}"
    return True, None


def validate_price_object(value: Any) -> Tuple[bool, Optional[str]]:
    """Validate price object"""
    if not isinstance(value, dict):
        return False, "Price must be an object"
    if "amount" not in value:
        return False, "Price amount is required"
    if "currency" not in value:
        return False, "Price currency is required"
    valid, err = validate_price_amount(value["amount"])
    if not valid:
        return False, f"amount: {err}"
    valid, err = validate_currency(value["currency"])
    if not valid:
        return False, f"currency: {err}"
    return True, None


def validate_line_item(item: Any) -> Tuple[bool, Optional[str]]:
    """Validate a line item"""
    if not isinstance(item, dict):
        return False, "Line item must be an object"
    if "productRef" not in item:
        return False, "productRef is required"
    if "quantity" not in item:
        return False, "quantity is required"
    valid, err = validate_uuid(item["productRef"])
    if not valid:
        return False, f"productRef: {err}"
    valid, err = validate_quantity(item["quantity"])
    if not valid:
        return False, f"quantity: {err}"
    return True, None


def validate_line_items(items: Any) -> Tuple[bool, Optional[str]]:
    """Validate line items array"""
    if not isinstance(items, list):
        return False, "Line items must be an array"
    if len(items) < 1:
        return False, "At least 1 line item is required"
    if len(items) > 100:
        return False, "Maximum 100 line items allowed"
    product_refs = set()
    for i, item in enumerate(items):
        valid, err = validate_line_item(item)
        if not valid:
            return False, f"lineItems[{i}]: {err}"
        # Check for duplicate productRef
        if item["productRef"] in product_refs:
            return False, f"Duplicate productRef in line items: {item['productRef']}"
        product_refs.add(item["productRef"])
    return True, None


def validate_billing_info(value: Any) -> Tuple[bool, Optional[str]]:
    """Validate billing info object"""
    if not isinstance(value, dict):
        return False, "Billing info must be an object"
    if "name" not in value:
        return False, "Billing name is required"
    if "address" not in value:
        return False, "Billing address is required"
    valid, err = validate_customer_name(value["name"])
    if not valid:
        return False, f"name: {err}"
    valid, err = validate_customer_address(value["address"])
    if not valid:
        return False, f"address: {err}"
    return True, None
