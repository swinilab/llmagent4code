from typing import List, Dict, AsyncGenerator
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.schemas import (
    CustomerCreate,
    ProductCreate,
    OrderCreate,
    PaymentCreate,
    InvoiceCreate,
    uuid_regex,
)
from app.repositories import (
    CustomerRepository,
    ProductRepository,
    OrderRepository,
    PaymentRepository,
    InvoiceRepository,
)
# Import the correct session provider and alias it to the name used in the original code for clarity
from app.db.connection_pool import get_session as get_db_session

# Create a router instance for FastAPI to register endpoints
router = APIRouter()

def to_dict(row):
    """Convert SQLAlchemy RowMapping or model instance to plain dict for JSONResponse."""
    if hasattr(row, "_mapping"):
        return dict(row._mapping)
    # Assume it's a model instance with __dict__ but hide private attrs
    data = {k: v for k, v in row.__dict__.items() if not k.startswith("_")}
    return data

# Customer endpoints
@router.post('/api/v1/customers', status_code=status.HTTP_201_CREATED)
async def create_customer(payload: CustomerCreate, session: AsyncSession = Depends(get_db_session)):
    customer = await CustomerRepository.create(session, payload)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=to_dict(customer))

@router.get('/api/v1/customers/{customer_id}')
async def get_customer(customer_id: str, session: AsyncSession = Depends(get_db_session)):
    if not uuid_regex.fullmatch(customer_id):
        raise HTTPException(status_code=400, detail='Invalid UUID')
    cust = await CustomerRepository.get_by_id(session, customer_id)
    if not cust:
        raise HTTPException(status_code=404, detail='Customer not found')
    return to_dict(cust)

# Product endpoints
@router.post('/api/v1/products', status_code=status.HTTP_201_CREATED)
async def create_product(payload: ProductCreate, session: AsyncSession = Depends(get_db_session)):
    product = await ProductRepository.create(session, payload)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=to_dict(product))

@router.get('/api/v1/products/{product_id}')
async def get_product(product_id: str, session: AsyncSession = Depends(get_db_session)):
    if not uuid_regex.fullmatch(product_id):
        raise HTTPException(status_code=400, detail='Invalid UUID')
    prod = await ProductRepository.get_by_id(session, product_id)
    if not prod:
        raise HTTPException(status_code=404, detail='Product not found')
    return to_dict(prod)

# Order endpoints
@router.post('/api/v1/orders', status_code=status.HTTP_201_CREATED)
async def create_order(payload: OrderCreate, session: AsyncSession = Depends(get_db_session)):
    # Validate customer exists
    cust = await CustomerRepository.get_by_id(session, payload.customerRef)
    if not cust:
        raise HTTPException(status_code=404, detail='Customer not found')
    # Validate each product exists and build line items
    line_items = []
    for li in payload.lineItems:
        prod = await ProductRepository.get_by_id(session, li.productRef)
        if not prod:
            raise HTTPException(status_code=404, detail='Product not found')
        line_items.append({"product_id": prod.id, "quantity": li.quantity})
    order = await OrderRepository.create(session, payload.customerRef, line_items)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=to_dict(order))

@router.get('/api/v1/orders/{order_id}')
async def get_order(order_id: str, session: AsyncSession = Depends(get_db_session)):
    if not uuid_regex.fullmatch(order_id):
        raise HTTPException(status_code=400, detail='Invalid UUID')
    order = await OrderRepository.get_by_id(session, order_id)
    if not order:
        raise HTTPException(status_code=404, detail='Order not found')
    return to_dict(order)

# Payment endpoints
@router.post('/api/v1/payments', status_code=status.HTTP_201_CREATED)
async def create_payment(payload: PaymentCreate, session: AsyncSession = Depends(get_db_session)):
    order = await OrderRepository.get_by_id(session, payload.orderRef)
    if not order:
        raise HTTPException(status_code=404, detail='Order not found')
    if order.status != 'INVOICED':
        raise HTTPException(status_code=409, detail='Order not invoiced')
    payment = await PaymentRepository.create(session, payload.orderRef, payload.amount, payload.method)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=to_dict(payment))

@router.get('/api/v1/payments/{payment_id}')
async def get_payment(payment_id: str, session: AsyncSession = Depends(get_db_session)):
    if not uuid_regex.fullmatch(payment_id):
        raise HTTPException(status_code=400, detail='Invalid UUID')
    payment = await PaymentRepository.get_by_id(session, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail='Payment not found')
    return to_dict(payment)

# Invoice endpoints
@router.post('/api/v1/invoices', status_code=status.HTTP_201_CREATED)
async def create_invoice(payload: InvoiceCreate, session: AsyncSession = Depends(get_db_session)):
    order = await OrderRepository.get_by_id(session, payload.orderRef)
    if not order:
        raise HTTPException(status_code=404, detail='Order not found')
    if order.status != 'ACCEPTED':
        raise HTTPException(status_code=409, detail='Order not accepted')
    # Build invoice fields from order snapshot
    invoice = await InvoiceRepository.create(
        session,
        order_id=payload.orderRef,
        billing_name=order.customer.name,
        billing_address=order.customer.address,
        total_amount=order.total_amount,
        issue_date=datetime.strptime(payload.issueDate, "%d/%m/%Y"),
        due_date=datetime.strptime(payload.dueDate, "%d/%m/%Y") if payload.dueDate else None,
    )
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=to_dict(invoice))

@router.get('/api/v1/invoices/{invoice_id}')
async def get_invoice(invoice_id: str, session: AsyncSession = Depends(get_db_session)):
    if not uuid_regex.fullmatch(invoice_id):
        raise HTTPException(status_code=400, detail='Invalid UUID')
    invoice = await InvoiceRepository.get_by_id(session, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail='Invoice not found')
    return to_dict(invoice)

__all__ = ["router"]
