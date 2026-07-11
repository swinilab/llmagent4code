"""
Customer REST router.
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from oms.database import get_db
from oms.models.entities import CustomerModel
from oms.repositories.customer_repo import CustomerRepository
from oms.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/customers", tags=["Customers"])


@router.post("", response_model=CustomerResponse, status_code=201)
def create_customer(data: CustomerCreate, db: Session = Depends(get_db)):
    repo = CustomerRepository(db)
    entity = CustomerModel(**data.model_dump())
    repo.create(entity)
    db.commit()
    db.refresh(entity)
    return entity


@router.get("", response_model=List[CustomerResponse])
def list_customers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    repo = CustomerRepository(db)
    return repo.list_all(skip, limit)


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    repo = CustomerRepository(db)
    entity = repo.get(customer_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Customer not found")
    return entity


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: str, data: CustomerUpdate, db: Session = Depends(get_db)
):
    repo = CustomerRepository(db)
    entity = repo.get(customer_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Customer not found")
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        return entity
    updated = repo.update_with_optimistic_lock(customer_id, updates, entity.version)
    if updated is None:
        raise HTTPException(status_code=409, detail="Concurrent modification detected")
    db.commit()
    return updated


@router.delete("/{customer_id}", status_code=204)
def delete_customer(customer_id: str, db: Session = Depends(get_db)):
    repo = CustomerRepository(db)
    if not repo.delete(customer_id):
        raise HTTPException(status_code=404, detail="Customer not found")
    db.commit()
