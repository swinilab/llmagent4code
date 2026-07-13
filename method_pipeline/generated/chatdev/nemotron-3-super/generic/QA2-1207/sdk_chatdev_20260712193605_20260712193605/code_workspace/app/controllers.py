from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from . import models, schemas, services
from .database import get_db
from . import dependencies

# Users
router_user = APIRouter(prefix="/api/v1/users", tags=["users"])

@router_user.post("/", response_model=schemas.UserInDB, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, user_service: services.UserService = Depends(dependencies.get_user_service)):
    db_user = user_service.get_user_by_email(user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return user_service.create_user(user)

@router_user.get("/{user_id}", response_model=schemas.UserInDB)
def read_user(user_id: int, user_service: services.UserService = Depends(dependencies.get_user_service)):
    db_user = user_service.get_user(user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router_user.get("/", response_model=list[schemas.UserInDB])
def read_users(skip: int = 0, limit: int = 100, user_service: services.UserService = Depends(dependencies.get_user_service)):
    return user_service.get_users(skip=skip, limit=limit)

@router_user.put("/{user_id}", response_model=schemas.UserInDB)
def update_user(user_id: int, user: schemas.UserUpdate, user_service: services.UserService = Depends(dependencies.get_user_service)):
    db_user = user_service.update_user(user_id, user)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router_user.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, user_service: services.UserService = Depends(dependencies.get_user_service)):
    success = user_service.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return None

# Products
router_product = APIRouter(prefix="/api/v1/products", tags=["products"])

@router_product.post("/", response_model=schemas.ProductInDB, status_code=status.HTTP_201_CREATED)
def create_product(product: schemas.ProductCreate, product_service: services.ProductService = Depends(dependencies.get_product_service)):
    return product_service.create_product(product)

@router_product.get("/{product_id}", response_model=schemas.ProductInDB)
def read_product(product_id: int, product_service: services.ProductService = Depends(dependencies.get_product_service)):
    db_product = product_service.get_product(product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

@router_product.get("/", response_model=list[schemas.ProductInDB])
def read_products(skip: int = 0, limit: int = 100, product_service: services.ProductService = Depends(dependencies.get_product_service)):
    return product_service.get_products(skip=skip, limit=limit)

@router_product.put("/{product_id}", response_model=schemas.ProductInDB)
def update_product(product_id: int, product: schemas.ProductUpdate, product_service: services.ProductService = Depends(dependencies.get_product_service)):
    db_product = product_service.update_product(product_id, product)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

@router_product.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, product_service: services.ProductService = Depends(dependencies.get_product_service)):
    success = product_service.delete_product(product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return None

# Orders
router_order = APIRouter(prefix="/api/v1/orders", tags=["orders"])

@router_order.post("/", response_model=schemas.OrderInDB, status_code=status.HTTP_201_CREATED)
def create_order(order: schemas.OrderCreate, order_service: services.OrderService = Depends(dependencies.get_order_service)):
    return order_service.create_order(order)

@router_order.get("/{order_id}", response_model=schemas.OrderInDB)
def read_order(order_id: int, order_service: services.OrderService = Depends(dependencies.get_order_service)):
    db_order = order_service.get_order(order_id)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order

@router_order.get("/", response_model=list[schemas.OrderInDB])
def read_orders(skip: int = 0, limit: int = 100, order_service: services.OrderService = Depends(dependencies.get_order_service)):
    return order_service.get_orders(skip=skip, limit=limit)

@router_order.put("/{order_id}", response_model=schemas.OrderInDB)
def update_order(order_id: int, order: schemas.OrderUpdate, order_service: services.OrderService = Depends(dependencies.get_order_service)):
    db_order = order_service.update_order(order_id, order)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order

@router_order.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, order_service: services.OrderService = Depends(dependencies.get_order_service)):
    success = order_service.delete_order(order_id)
    if not success:
        raise HTTPException(status_code=404, detail="Order not found")
    return None

# Order workflow
@router_order.post("/{order_id}/accept", response_model=schemas.OrderInDB)
def accept_order(order_id: int, order_service: services.OrderService = Depends(dependencies.get_order_service)):
    order = order_service.accept_order(order_id)
    if order is None:
        raise HTTPException(status_code=400, detail="Order cannot be accepted")
    return order

@router_order.post("/{order_id}/invoice", response_model=schemas.InvoiceInDB)
def create_invoice_for_order(order_id: int, billing_info: str, order_service: services.OrderService = Depends(dependencies.get_order_service)):
    invoice = order_service.create_invoice_for_order(order_id, billing_info)
    if invoice is None:
        raise HTTPException(status_code=400, detail="Invoice cannot be created")
    return invoice

@router_order.post("/{order_id}/pay", response_model=schemas.PaymentInDB)
def process_payment(order_id: int, amount: int, method: str, order_service: services.OrderService = Depends(dependencies.get_order_service)):
    payment = order_service.record_payment(order_id, amount, method)
    if payment is None:
        raise HTTPException(status_code=400, detail="Payment cannot be processed")
    return payment

@router_order.post("/payments/{payment_id}/verify", response_model=schemas.PaymentInDB)
def verify_payment(payment_id: int, order_service: services.OrderService = Depends(dependencies.get_order_service)):
    payment = order_service.verify_payment(payment_id)
    if payment is None:
        raise HTTPException(status_code=400, detail="Payment cannot be verified")
    return payment

@router_order.post("/{order_id}/ship", response_model=schemas.OrderInDB)
def ship_order(order_id: int, order_service: services.OrderService = Depends(dependencies.get_order_service)):
    order = order_service.ship_order(order_id)
    if order is None:
        raise HTTPException(status_code=400, detail="Order cannot be shipped")
    return order

@router_order.post("/{order_id}/close", response_model=schemas.OrderInDB)
def close_order(order_id: int, order_service: services.OrderService = Depends(dependencies.get_order_service)):
    order = order_service.close_order(order_id)
    if order is None:
        raise HTTPException(status_code=400, detail="Order cannot be closed")
    return order

# Payments
router_payment = APIRouter(prefix="/api/v1/payments", tags=["payments"])

@router_payment.post("/", response_model=schemas.PaymentInDB, status_code=status.HTTP_201_CREATED)
def create_payment(payment: schemas.PaymentCreate, payment_service: services.PaymentService = Depends(dependencies.get_payment_service)):
    return payment_service.create_payment(payment)

@router_payment.get("/{payment_id}", response_model=schemas.PaymentInDB)
def read_payment(payment_id: int, payment_service: services.PaymentService = Depends(dependencies.get_payment_service)):
    db_payment = payment_service.get_payment(payment_id)
    if db_payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return db_payment

@router_payment.get("/order/{order_id}", response_model=list[schemas.PaymentInDB])
def read_payments_by_order(order_id: int, payment_service: services.PaymentService = Depends(dependencies.get_payment_service)):
    return payment_service.get_payments_by_order(order_id)

@router_payment.put("/{payment_id}", response_model=schemas.PaymentInDB)
def update_payment(payment_id: int, payment: schemas.PaymentUpdate, payment_service: services.PaymentService = Depends(dependencies.get_payment_service)):
    db_payment = payment_service.update_payment(payment_id, payment)
    if db_payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return db_payment

@router_payment.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment(payment_id: int, payment_service: services.PaymentService = Depends(dependencies.get_payment_service)):
    success = payment_service.delete_payment(payment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Payment not found")
    return None

# Invoices
router_invoice = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])

@router_invoice.post("/", response_model=schemas.InvoiceInDB, status_code=status.HTTP_201_CREATED)
def create_invoice(invoice: schemas.InvoiceCreate, invoice_service: services.InvoiceService = Depends(dependencies.get_invoice_service)):
    return invoice_service.create_invoice(invoice)

@router_invoice.get("/{invoice_id}", response_model=schemas.InvoiceInDB)
def read_invoice(invoice_id: int, invoice_service: services.InvoiceService = Depends(dependencies.get_invoice_service)):
    db_invoice = invoice_service.get_invoice(invoice_id)
    if db_invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return db_invoice

@router_invoice.get("/order/{order_id}", response_model=schemas.InvoiceInDB)
def read_invoice_by_order(order_id: int, invoice_service: services.InvoiceService = Depends(dependencies.get_invoice_service)):
    db_invoice = invoice_service.get_invoice_by_order(order_id)
    if db_invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return db_invoice

@router_invoice.put("/{invoice_id}", response_model=schemas.InvoiceInDB)
def update_invoice(invoice_id: int, invoice: schemas.InvoiceUpdate, invoice_service: services.InvoiceService = Depends(dependencies.get_invoice_service)):
    db_invoice = invoice_service.update_invoice(invoice_id, invoice)
    if db_invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return db_invoice

@router_invoice.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(invoice_id: int, invoice_service: services.InvoiceService = Depends(dependencies.get_invoice_service)):
    success = invoice_service.delete_invoice(invoice_id)
    if not success:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return None

@router_invoice.post("/{invoice_id}/approve", response_model=schemas.InvoiceInDB)
def approve_invoice(invoice_id: int, invoice_service: services.InvoiceService = Depends(dependencies.get_invoice_service)):
    invoice = invoice_service.approve_invoice(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=400, detail="Invoice cannot be approved")
    return invoice

@router_invoice.post("/{invoice_id}/pay", response_model=schemas.InvoiceInDB)
def mark_invoice_as_paid(invoice_id: int, invoice_service: services.InvoiceService = Depends(dependencies.get_invoice_service)):
    invoice = invoice_service.mark_invoice_as_paid(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=400, detail="Invoice cannot be marked as paid")
    return invoice