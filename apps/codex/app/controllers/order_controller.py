from app.controllers.common import parse_identifier
from app.domain.schemas import OrderCreate, OrderResponse, OrderWorkflowResponse
from app.services.order_service import OrderService


class OrderController:
    def __init__(self, service: OrderService) -> None:
        self.service = service

    async def create(self, request: OrderCreate) -> OrderResponse:
        return await self.service.create(request)

    async def get(self, order_id: str) -> OrderResponse:
        return await self.service.get(parse_identifier(order_id))

    async def accept(self, order_id: str) -> OrderWorkflowResponse:
        return await self.service.accept(parse_identifier(order_id))

    async def ship(self, order_id: str) -> OrderWorkflowResponse:
        return await self.service.ship(parse_identifier(order_id))

    async def close(self, order_id: str) -> OrderWorkflowResponse:
        return await self.service.close(parse_identifier(order_id))

    async def cancel(self, order_id: str) -> OrderWorkflowResponse:
        return await self.service.cancel(parse_identifier(order_id))

