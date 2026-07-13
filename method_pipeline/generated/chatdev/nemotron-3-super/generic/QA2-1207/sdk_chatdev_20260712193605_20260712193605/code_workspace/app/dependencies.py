from sqlalchemy.orm import Session
from fastapi import Depends
from . import services
from .database import get_db

def get_user_service(db: Session = Depends(get_db)):
    return services.UserService(db)

def get_product_service(db: Session = Depends(get_db)):
    return services.ProductService(db)

def get_order_service(db: Session = Depends(get_db)):
    return services.OrderService(db)

def get_payment_service(db: Session = Depends(get_db)):
    return services.PaymentService(db)

def get_invoice_service(db: Session = Depends(get_db)):
    return services.InvoiceService(db)