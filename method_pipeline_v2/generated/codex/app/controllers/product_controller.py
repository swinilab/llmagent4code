from app.controllers.common import parse_identifier
from app.domain.schemas import ProductCreate, ProductResponse
from app.services.product_service import ProductService


class ProductController:
    def __init__(self, service: ProductService) -> None:
        self.service = service

    async def create(self, request: ProductCreate) -> ProductResponse:
        return await self.service.create(request)

    async def get(self, product_id: str) -> ProductResponse:
        return await self.service.get(parse_identifier(product_id))

