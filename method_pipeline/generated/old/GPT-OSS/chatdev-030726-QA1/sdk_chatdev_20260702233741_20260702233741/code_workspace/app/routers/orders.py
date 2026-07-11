# app/routers/orders.py
"""Order endpoints and workflow actions."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import schemas, services, database, models

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])

def get_order_service(db: Session = Depends(database.get_db)):
    return services.OrderService(db)

def get_invoice_service(db: Session = Depends(database.get_db)):
    return services.InvoiceService(db)

def get_payment_service(db: Session = Depends(database.get_db)):
    return services.PaymentService(db)

def get_shipping_service(db: Session = Depends(database.get_db)):
    return services.ShippingService(db)

@router.post("/", response_model=schemas.OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(payload: schemas.OrderCreate, svc: services.OrderService = Depends(get_order_service)):
    return svc.place_order(payload)

@router.get("/{order_id}", response_model=schemas.OrderRead)
def get_order(order_id: int, svc: services.OrderService = Depends(get_order_service)):
    order = svc.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

# Staff accepts order
@router.post("/{order_id}/accept", response_model=schemas.OrderRead)
def accept_order(order_id: int, svc: services.OrderService = Depends(get_order_service)):
    return svc.accept_order(order_id)

# Accountant creates invoice
@router.post("/{order_id}/invoice", response_model=schemas.InvoiceRead)
def create_invoice(order_id: int, payload: schemas.InvoiceCreate, svc: services.InvoiceService = Depends(get_invoice_service)):
    if payload.order_id != order_id:
        raise HTTPException(status_code=400, detail="Payload order_id mismatch")
    return svc.create_invoice(order_id, payload)

# Customer pays invoice (creates payment)
@router.post("/{order_id}/pay", response_model=schemas.PaymentRead)
def pay_invoice(order_id: int, payload: schemas.PaymentCreate, svc: services.PaymentService = Depends(get_payment_service)):
    if payload.order_id != order_id:
        raise HTTPException(status_code=400, detail="Payload order_id mismatch")
    return svc.create_payment(payload)

# Accountant verifies payment (simulated)
@router.post("/{order_id}/verify-payment", response_model=schemas.PaymentRead)
def verify_payment(order_id: int, success: bool, svc: services.PaymentService = Depends(get_payment_service)):
    # Find payment for order
    payment = svc.db.query(models.Payment).filter(models.Payment.order_id == order_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found for order")
    return svc.verify_payment(payment.id, success)

# Staff ships order
@router.post("/{order_id}/ship", response_model=schemas.OrderRead)
def ship_order(order_id: int, svc: services.ShippingService = Depends(get_shipping_service)):
    return svc.ship_order(order_id)

# Staff closes order
@router.post("/{order_id}/close", response_model=schemas.OrderRead)
def close_order(order_id: int, svc: services.ShippingService = Depends(get_shipping_service)):
    return svc.close_order(order_id)
