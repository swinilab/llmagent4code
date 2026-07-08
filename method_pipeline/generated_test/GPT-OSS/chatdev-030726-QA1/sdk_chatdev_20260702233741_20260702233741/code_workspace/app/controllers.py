from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session

from app import schemas, services, models, repositories
from app.dependencies import get_db

router = APIRouter()

# Customer endpoints
@router.post('/customers', response_model=schemas.CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(customer_in: schemas.CustomerCreate, db: Session = Depends(get_db)):
    repo = repositories.CustomerRepository(db)
    customer = models.Customer(**customer_in.dict())
    return repo.create(customer)
    repo = repositories.CustomerRepository(db)
    customer = models.Customer(**customer_in.dict())
def create_product(product_in: schemas.ProductCreate, db: Session = Depends(get_db)):
    repo = repositories.ProductRepository(db)
    product = models.Product(**product_in.dict())
    return repo.create(product)
def list_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    repo = repositories.ProductRepository(db)
    return repo.list(skip, limit)
# Product endpoints
@router.post('/products', response_model=schemas.ProductRead, status_code=status.HTTP_201_CREATED)
def place_order(order_in: schemas.OrderCreate, db: Session = Depends(get_db)):
    svc = services.OrderService(db)
    order = svc.place_order(order_in)
    return order
def accept_order(order_id: int, db: Session = Depends(get_db)):
    svc = services.OrderService(db)
    return svc.accept_order(order_id)
    product = models.Product(**product_in.dict())
def create_invoice(order_id: int, invoice_in: schemas.InvoiceCreate, db: Session = Depends(get_db)):
    svc = services.OrderService(db)
    return svc.create_invoice(order_id, invoice_in)

def record_payment(payment_in: schemas.PaymentCreate, db: Session = Depends(get_db)):
    svc = services.OrderService(db)
    return svc.record_payment(payment_in)
def list_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
def verify_payment(payment_id: int, success: bool, db: Session = Depends(get_db)):
    svc = services.OrderService(db)
    return svc.verify_payment(payment_id, success)
    return repo.list(skip, limit)
def ship_order(order_id: int, db: Session = Depends(get_db)):
    svc = services.OrderService(db)
    return svc.ship_order(order_id)
# Order workflow endpoints
def close_order(order_id: int, db: Session = Depends(get_db)):
    svc = services.OrderService(db)
    return svc.close_order(order_id)
def place_order(order_in: schemas.OrderCreate, db: Session = Depends(get_db)):
    svc = services.OrderService(db)
    order = svc.place_order(order_in)
    return order

@router.post('/orders/{order_id}/accept', response_model=schemas.OrderRead)
def accept_order(order_id: int, db: Session = Depends(get_db)):
    svc = services.OrderService(db)
    return svc.accept_order(order_id)

@router.post('/orders/{order_id}/invoice', response_model=schemas.InvoiceRead)
def create_invoice(order_id: int, invoice_in: schemas.InvoiceCreate, db: Session = Depends(get_db)):
    svc = services.OrderService(db)
    return svc.create_invoice(order_id, invoice_in)

@router.post('/payments', response_model=schemas.PaymentRead, status_code=status.HTTP_201_CREATED)
def record_payment(payment_in: schemas.PaymentCreate, db: Session = Depends(get_db)):
    svc = services.OrderService(db)
    return svc.record_payment(payment_in)

@router.post('/payments/{payment_id}/verify', response_model=schemas.PaymentRead)
def verify_payment(payment_id: int, success: bool, db: Session = Depends(get_db)):
    svc = services.OrderService(db)
    return svc.verify_payment(payment_id, success)

@router.post('/orders/{order_id}/ship', response_model=schemas.OrderRead)
def ship_order(order_id: int, db: Session = Depends(get_db)):
    svc = services.OrderService(db)
    return svc.ship_order(order_id)

@router.post('/orders/{order_id}/close', response_model=schemas.OrderRead)
def close_order(order_id: int, db: Session = Depends(get_db)):
    svc = services.OrderService(db)
    return svc.close_order(order_id)
