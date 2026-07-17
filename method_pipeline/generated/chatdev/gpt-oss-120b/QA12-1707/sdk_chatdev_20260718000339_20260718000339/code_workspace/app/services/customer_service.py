"""Customer service handling customer related operations."""

from sqlmodel import Session, select
from typing import Optional, List

from ..models import Customer, Order
from ..database import get_session

class CustomerService:
    @staticmethod
    def get_customer(session: Session, customer_id: int) -> Optional[Customer]:
        return session.get(Customer, customer_id)

    @staticmethod
    def create_customer(session: Session, *, name: str, address: str, phone: str, banking_details: str) -> Customer:
        customer = Customer(name=name, address=address, phone=phone, banking_details=banking_details)
        session.add(customer)
        session.commit()
        session.refresh(customer)
        return customer

    @staticmethod
    def list_customers(session: Session) -> List[Customer]:
        return session.exec(select(Customer)).all()
