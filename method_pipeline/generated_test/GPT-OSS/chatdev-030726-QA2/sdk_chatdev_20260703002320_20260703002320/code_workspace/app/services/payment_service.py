"""
Payment service handling payment recording and verification.
"""

from sqlalchemy.orm import Session
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import PaymentCreate

class PaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PaymentRepository()

    def record_payment(self, payload: PaymentCreate):
        # Business rule: amount must match invoice amount (not enforced here)
        return self.repo.create(self.db, payload.model_dump())

    def get_payment(self, payment_id: int):
        return self.repo.get(self.db, payment_id)
