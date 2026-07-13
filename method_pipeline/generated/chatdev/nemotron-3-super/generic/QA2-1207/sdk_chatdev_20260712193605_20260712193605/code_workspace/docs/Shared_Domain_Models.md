# Shared Domain Models

## Overview
The shared domain models are the data structures that are exchanged between the frontend and backend (or between different services in a microservice architecture). In this backend-only implementation, these models define the request and response bodies for the API endpoints.

## Location
The shared models are defined in `app/schemas.py` using Pydantic's `BaseModel`. These models are used for:
- Request body validation
- Response serialization
- Automatic OpenAPI documentation generation

## Models

### User
- **UserBase**: Common fields (name, address, phone, banking_details, role)
- **UserCreate**: Extends UserBase with password
- **UserUpdate**: Partial update model for user fields
- **UserInDB**: Includes database fields (id, is_active, created_at, updated_at)
- **UserInDBBase**: Base for database representation (without hashed password)
- **UserResponse**: Model for returning user data (excluding sensitive fields)

### Product
- **ProductBase**: Description, base_price (in cents), currency
- **ProductCreate**: For creating a new product
- **ProductUpdate**: Partial update model
- **ProductInDB**: Includes database fields (id, is_active, timestamps)
- **ProductResponse**: For returning product data

### OrderItem
- **OrderItemBase**: Product ID, quantity, unit price (in cents), total price (in cents)
- **OrderItemCreate**: For creating an order item
- **OrderItemUpdate**: Partial update model
- **OrderItemInDB**: Includes database fields (id, order_id)
- **OrderItemResponse**: For returning order item data

### Order
- **OrderBase**: Customer ID, status, total amount (in cents), invoice ID (optional)
- **OrderCreate**: Extends OrderBase with a list of OrderItemCreate
- **OrderUpdate**: Partial update model for order fields
- **OrderInDB**: Includes database fields (id, timestamps) and nested OrderItemResponse list
- **OrderResponse**: For returning order data with calculated total amount

### Payment
- **PaymentBase**: Order ID, amount (in cents), method, status
- **PaymentCreate**: For creating a payment record
- **PaymentUpdate**: Partial update model
- **PaymentInDB**: Includes database fields (id, timestamp)
- **PaymentResponse**: For returning payment data

### Invoice
- **InvoiceBase**: Order ID, billing info (text), amount (in cents), issue date, due date, status
- **InvoiceCreate**: For creating an invoice
- **InvoiceUpdate**: Partial update model
- **InvoiceInDB**: Includes database fields (id, timestamps)
- **InvoiceResponse**: For returning invoice data

## Usage
These models are imported and used in:
- **Controllers**: To define request and response models for API endpoints.
- **Services**: To validate input and output data.
- **Repositories**: Typically return ORM models, which are then converted to Pydantic models by the services.

## Validation
Pydantic provides automatic data validation, type conversion, and error messages. For example:
- Fields with `gt=0` ensure positive numbers.
- Email fields use `EmailStr` for validation.
- Enums ensure that only predefined values are allowed.

## Extensibility
To add a new field to a model:
1. Add the field to the appropriate base model (e.g., `ProductBase`).
2. Update the create/update models if the field should be editable.
3. Ensure the ORM model (`app/models.py`) is updated accordingly.
4. The migration script (if using Alembic) will need to adjust the database schema.

## Security Note
Sensitive fields (e.g., banking_details, hashed passwords) are excluded from response models to prevent accidental exposure.