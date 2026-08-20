from app.controllers.common import parse_identifier
from app.domain.schemas import CustomerCreate, CustomerResponse
from app.services.customer_service import CustomerService


class CustomerController:
    def __init__(self, service: CustomerService) -> None:
        self.service = service

    async def create(self, request: CustomerCreate) -> CustomerResponse:
        return await self.service.create(request)

    async def get(self, customer_id: str) -> CustomerResponse:
        return await self.service.get(parse_identifier(customer_id))

