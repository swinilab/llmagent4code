from app.controllers.common import parse_identifier
from app.domain.schemas import PaymentCreate, PaymentResponse, PaymentWorkflowResponse
from app.services.payment_service import PaymentService


class PaymentController:
    def __init__(self, service: PaymentService) -> None:
        self.service = service

    async def create(self, request: PaymentCreate) -> PaymentResponse:
        return await self.service.create(request)

    async def get(self, payment_id: str) -> PaymentResponse:
        return await self.service.get(parse_identifier(payment_id))

    async def verify(self, payment_id: str) -> PaymentWorkflowResponse:
        return await self.service.verify(parse_identifier(payment_id))

    async def reject(self, payment_id: str) -> PaymentWorkflowResponse:
        return await self.service.reject(parse_identifier(payment_id))

