"""
Domain models for OMS
Implements all entities from the Domain Model with Field Constraint Table validation
"""
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator
from oms_backend.utils.validators import (
    validate_uuid,
    validate_customer_name,
    validate_customer_address,
    validate_customer_phone,
    validate_account_number,
    validate_bank_name,
    validate_customer_role,
    validate_product_description,
    validate_price_amount,
    validate_currency,
    validate_order_status,
    validate_payment_status,
    validate_payment_method,
    validate_invoice_status,
    validate_quantity,
    validate_total_amount,
    validate_date_ddmmyyyy,
    validate_banking_details,
    validate_price_object,
    validate_line_items,
    validate_billing_info,
    ALLOWED_CUSTOMER_ROLES,
    ALLOWED_ORDER_STATUSES,
    ALLOWED_PAYMENT_STATUSES,
    ALLOWED_PAYMENT_METHODS,
    ALLOWED_INVOICE_STATUSES,
    SUPPORTED_CURRENCIES,
)


# ============== Customer ==============

class BankingDetails(BaseModel):
    """Banking details for customer"""
    accountNumber: str = Field(..., description="Bank account number (6-20 digits)")
    bankName: str = Field(..., description="Bank name (2-100 characters)")
    
    @field_validator("accountNumber")
    @classmethod
    def validate_account_number(cls, v: str) -> str:
        valid, err = validate_account_number(v)
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("bankName")
    @classmethod
    def validate_bank_name(cls, v: str) -> str:
        valid, err = validate_bank_name(v)
        if not valid:
            raise ValueError(err)
        return v


class Customer(BaseModel):
    """
    Customer entity
    Implements all constraints from Field Constraint Table for Customer
    """
    id: Optional[UUID] = Field(None, description="Customer ID (UUIDv4, server-generated)")
    name: str = Field(..., description="Customer name (2-100 chars)")
    address: str = Field(..., description="Customer address (5-255 chars)")
    phone: str = Field(..., description="Customer phone (E.164 format)")
    bankingDetails: BankingDetails = Field(..., description="Banking details")
    role: str = Field(default="CUSTOMER", description="Customer role")
    orderHistory: Optional[List[UUID]] = Field(None, description="Order history")
    createdAt: Optional[datetime] = Field(None, description="Creation timestamp")
    updatedAt: Optional[datetime] = Field(None, description="Last update timestamp")
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        valid, err = validate_customer_name(v)
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        valid, err = validate_customer_address(v)
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        valid, err = validate_customer_phone(v)
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        valid, err = validate_customer_role(v)
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("bankingDetails")
    @classmethod
    def validate_banking_details(cls, v: BankingDetails) -> BankingDetails:
        valid, err = validate_banking_details(v.model_dump())
        if not valid:
            raise ValueError(err)
        return v


class CustomerCreate(BaseModel):
    """DTO for creating a customer"""
    name: str
    address: str
    phone: str
    bankingDetails: BankingDetails
    role: str = "CUSTOMER"
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        valid, err = validate_customer_name(v)
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        valid, err = validate_customer_address(v)
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        valid, err = validate_customer_phone(v)
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        valid, err = validate_customer_role(v)
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("bankingDetails")
    @classmethod
    def validate_banking_details(cls, v: BankingDetails) -> BankingDetails:
        valid, err = validate_banking_details(v.model_dump())
        if not valid:
            raise ValueError(err)
        return v


# ============== Product ==============

class Price(BaseModel):
    """Price object with amount and currency"""
    amount: str = Field(..., description="Price amount (exactly 2 decimal places)")
    currency: str = Field(..., description="Currency code (ISO 4217)")
    
    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Any) -> str:
        if isinstance(v, (int, float)):
            v = f"{v:.2f}"
        valid, err = validate_price_amount(v)
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        valid, err = validate_currency(v)
        if not valid:
            raise ValueError(err)
        return v


class Product(BaseModel):
    """
    Product entity
    Implements all constraints from Field Constraint Table for Product
    """
    id: Optional[UUID] = Field(None, description="Product ID (UUIDv4, server-generated)")
    description: str = Field(..., description="Product description (3-500 chars)")
    price: Price = Field(..., description="Product price")
    createdAt: Optional[datetime] = Field(None, description="Creation timestamp")
    updatedAt: Optional[datetime] = Field(None, description="Last update timestamp")
    
    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        valid, err = validate_product_description(v)
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Price) -> Price:
        valid, err = validate_price_object(v.model_dump())
        if not valid:
            raise ValueError(err)
        return v


class ProductCreate(BaseModel):
    """DTO for creating a product"""
    description: str
    price: Price
    
    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        valid, err = validate_product_description(v)
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Price) -> Price:
        valid, err = validate_price_object(v.model_dump())
        if not valid:
            raise ValueError(err)
        return v


# ============== Order ==============

class LineItem(BaseModel):
    """Line item in an order"""
    productRef: UUID = Field(..., description="Reference to product")
    quantity: int = Field(..., description="Quantity (1-1000)")
    unitPriceSnapshot: Optional[str] = Field(None, description="Price snapshot at order time")
    
    @field_validator("productRef")
    @classmethod
    def validate_product_ref(cls, v: UUID) -> UUID:
        valid, err = validate_uuid(str(v))
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        valid, err = validate_quantity(v)
        if not valid:
            raise ValueError(err)
        return v


class Order(BaseModel):
    """
    Order entity
    Implements all constraints from Field Constraint Table for Order
    """
    id: Optional[UUID] = Field(None, description="Order ID (UUIDv4, server-generated)")
    customerRef: UUID = Field(..., description="Reference to customer")
    lineItems: List[LineItem] = Field(..., description="Order line items")
    totalAmount: Optional[str] = Field(None, description="Total amount (server-computed)")
    status: str = Field(default="PLACED", description="Order status")
    invoiceRef: Optional[UUID] = Field(None, description="Reference to invoice")
    createdAt: Optional[datetime] = Field(None, description="Creation timestamp")
    updatedAt: Optional[datetime] = Field(None, description="Last update timestamp")
    
    @field_validator("customerRef")
    @classmethod
    def validate_customer_ref(cls, v: UUID) -> UUID:
        valid, err = validate_uuid(str(v))
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("lineItems")
    @classmethod
    def validate_line_items(cls, v: List[LineItem]) -> List[LineItem]:
        valid, err = validate_line_items([item.model_dump() for item in v])
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid, err = validate_order_status(v)
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("invoiceRef")
    @classmethod
    def validate_invoice_ref(cls, v: Optional[UUID]) -> Optional[UUID]:
        if v is not None:
            valid, err = validate_uuid(str(v))
            if not valid:
                raise ValueError(err)
        return v


class OrderCreate(BaseModel):
    """DTO for creating an order"""
    customerRef: UUID
    lineItems: List[LineItem]
    
    @field_validator("customerRef")
    @classmethod
    def validate_customer_ref(cls, v: UUID) -> UUID:
        valid, err = validate_uuid(str(v))
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("lineItems")
    @classmethod
    def validate_line_items(cls, v: List[LineItem]) -> List[LineItem]:
        valid, err = validate_line_items([item.model_dump() for item in v])
        if not valid:
            raise ValueError(err)
        return v


# ============== Payment ==============

class Payment(BaseModel):
    """
    Payment entity
    Implements all constraints from Field Constraint Table for Payment
    """
    id: Optional[UUID] = Field(None, description="Payment ID (UUIDv4, server-generated)")
    orderRef: UUID = Field(..., description="Reference to order")
    amount: str = Field(..., description="Payment amount")
    timestamp: Optional[datetime] = Field(None, description="Payment timestamp")
    status: str = Field(default="PENDING", description="Payment status")
    method: str = Field(..., description="Payment method")
    
    @field_validator("orderRef")
    @classmethod
    def validate_order_ref(cls, v: UUID) -> UUID:
        valid, err = validate_uuid(str(v))
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Any) -> str:
        if isinstance(v, (int, float)):
            v = f"{v:.2f}"
        valid, err = validate_total_amount(v)
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid, err = validate_payment_status(v)
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        valid, err = validate_payment_method(v)
        if not valid:
            raise ValueError(err)
        return v


class PaymentCreate(BaseModel):
    """DTO for creating a payment"""
    orderRef: UUID
    amount: Any
    method: str
    
    @field_validator("orderRef")
    @classmethod
    def validate_order_ref(cls, v: UUID) -> UUID:
        valid, err = validate_uuid(str(v))
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Any) -> str:
        if isinstance(v, (int, float)):
            v = f"{v:.2f}"
        valid, err = validate_total_amount(v)
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        valid, err = validate_payment_method(v)
        if not valid:
            raise ValueError(err)
        return v


# ============== Invoice ==============

class BillingInfo(BaseModel):
    """Billing information for invoice"""
    name: str = Field(..., description="Billing name")
    address: str = Field(..., description="Billing address")
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        valid, err = validate_customer_name(v)
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        valid, err = validate_customer_address(v)
        if not valid:
            raise ValueError(err)
        return v


class Invoice(BaseModel):
    """
    Invoice entity
    Implements all constraints from Field Constraint Table for Invoice
    """
    id: Optional[UUID] = Field(None, description="Invoice ID (UUIDv4, server-generated)")
    orderRef: UUID = Field(..., description="Reference to order")
    billingInfo: BillingInfo = Field(..., description="Billing information")
    totalAmount: str = Field(..., description="Invoice total amount")
    issueDate: str = Field(..., description="Issue date (dd/MM/yyyy)")
    dueDate: str = Field(..., description="Due date (dd/MM/yyyy)")
    status: str = Field(default="ISSUED", description="Invoice status")
    
    @field_validator("orderRef")
    @classmethod
    def validate_order_ref(cls, v: UUID) -> UUID:
        valid, err = validate_uuid(str(v))
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("billingInfo")
    @classmethod
    def validate_billing_info(cls, v: BillingInfo) -> BillingInfo:
        valid, err = validate_billing_info(v.model_dump())
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("totalAmount")
    @classmethod
    def validate_total_amount(cls, v: Any) -> str:
        if isinstance(v, (int, float)):
            v = f"{v:.2f}"
        valid, err = validate_total_amount(v)
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("issueDate")
    @classmethod
    def validate_issue_date(cls, v: str) -> str:
        valid, err = validate_date_ddmmyyyy(v)
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("dueDate")
    @classmethod
    def validate_due_date(cls, v: str) -> str:
        valid, err = validate_date_ddmmyyyy(v)
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid, err = validate_invoice_status(v)
        if not valid:
            raise ValueError(err)
        return v
    
    @model_validator(mode="after")
    def validate_dates(self) -> "Invoice":
        """Validate that dueDate >= issueDate"""
        issue = datetime.strptime(self.issueDate, "%d/%m/%Y").date()
        due = datetime.strptime(self.dueDate, "%d/%m/%Y").date()
        if due < issue:
            raise ValueError("dueDate must be >= issueDate")
        return self


class InvoiceCreate(BaseModel):
    """DTO for creating an invoice"""
    orderRef: UUID
    billingInfo: BillingInfo
    totalAmount: Any
    issueDate: Optional[str] = None
    dueDate: Optional[str] = None
    
    @field_validator("orderRef")
    @classmethod
    def validate_order_ref(cls, v: UUID) -> UUID:
        valid, err = validate_uuid(str(v))
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("billingInfo")
    @classmethod
    def validate_billing_info(cls, v: BillingInfo) -> BillingInfo:
        valid, err = validate_billing_info(v.model_dump())
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("totalAmount")
    @classmethod
    def validate_total_amount(cls, v: Any) -> str:
        if isinstance(v, (int, float)):
            v = f"{v:.2f}"
        valid, err = validate_total_amount(v)
        if not valid:
            raise ValueError(err)
        return v
    
    @field_validator("issueDate")
    @classmethod
    def validate_issue_date(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid, err = validate_date_ddmmyyyy(v)
            if not valid:
                raise ValueError(err)
        return v
    
    @field_validator("dueDate")
    @classmethod
    def validate_due_date(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid, err = validate_date_ddmmyyyy(v)
            if not valid:
                raise ValueError(err)
        return v
