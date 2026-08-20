from app.controllers.common import parse_identifier
from app.domain.schemas import InvoiceCreate, InvoiceResponse
from app.services.invoice_service import InvoiceService


class InvoiceController:
    def __init__(self, service: InvoiceService) -> None:
        self.service = service

    async def create(self, request: InvoiceCreate) -> InvoiceResponse:
        return await self.service.create(request)

    async def get(self, invoice_id: str) -> InvoiceResponse:
        return await self.service.get(parse_identifier(invoice_id))

