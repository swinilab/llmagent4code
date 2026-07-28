from fastapi import APIRouter, HTTPException
import uuid

from app.models import CustomerCreateDTO, CustomerDTO
from app.repositories import CustomerRepository

router = APIRouter()

@router.post('', response_model=CustomerDTO)
def create_customer(dto: CustomerCreateDTO):
    # Server generate UUID
    customer_id = str(uuid.uuid4())
    customer = CustomerDTO(
        id=customer_id,
        name=dto.name,
        address=dto.address,
        phone=dto.phone,
        bankingDetails=dto.bankingDetails,
        role=dto.role,
        orderHistory=[],
    )
    CustomerRepository.create(customer)
    return customer

@router.get('/{customer_id}', response_model=CustomerDTO)
def get_customer(customer_id: str):
    cust = CustomerRepository.get_by_id(customer_id)
    if not cust:
        raise HTTPException(status_code=404, detail='Customer not found')
    return cust
