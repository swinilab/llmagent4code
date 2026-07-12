"""
CustomerService — business logic for customer management.
All methods are async and expect an active DB session with active transaction.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from oms_backend.models.orm_models import Customer
from oms_backend.repositories.entities import CustomerRepository
from oms_backend.schemas.domain import Address, CustomerCreate, CustomerUpdate
from oms_backend.services.utils import audit_log


class CustomerService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = CustomerRepository(session)

    async def create(self, data: CustomerCreate, actor_id: uuid.UUID | None = None, ip_address: str | None = None) -> Customer:
        code = await self.repo.next_code()
        customer = await self.repo.create(
            code=code,
            name=data.name,
            email=data.email.lower().strip(),
            phone=data.phone,
            role=data.role.value,
            address_line1=data.address.line1,
            address_line2=data.address.line2,
            city=data.address.city,
            state=data.address.state,
            postal_code=data.address.postal_code,
            country=data.address.country,
            bank_name=data.bank_name,
            bank_account=data.bank_account,
            bank_routing=data.bank_routing,
            created_by=actor_id,
        )
        await audit_log(self.session, "customer", customer.id, "created", actor_id=actor_id, ip_address=ip_address)
        return customer

    async def get(self, id: uuid.UUID) -> Customer | None:
        return await self.repo.get_active(id)

    async def get_by_email(self, email: str) -> Customer | None:
        return await self.repo.get_by_email(email)

    async def update(self, id: uuid.UUID, data: CustomerUpdate, actor_id: uuid.UUID | None = None, ip_address: str | None = None) -> Customer | None:
        customer = await self.repo.get_active(id)
        if not customer:
            return None

        update_data: dict[str, Any] = {}
        if data.name is not None:
            update_data["name"] = data.name
        if data.email is not None:
            update_data["email"] = data.email.lower().strip()
        if data.phone is not None:
            update_data["phone"] = data.phone
        if data.address is not None:
            update_data.update(
                address_line1=data.address.line1,
                address_line2=data.address.line2,
                city=data.address.city,
                state=data.address.state,
                postal_code=data.address.postal_code,
                country=data.address.country,
            )
        if data.bank_name is not None:
            update_data["bank_name"] = data.bank_name
        if data.bank_account is not None:
            update_data["bank_account"] = data.bank_account
        if data.bank_routing is not None:
            update_data["bank_routing"] = data.bank_routing

        if update_data:
            updated = await self.repo.update(id, **update_data)
            if updated:
                await audit_log(self.session, "customer", id, "updated", actor_id=actor_id, payload=update_data, ip_address=ip_address)
            return updated
        return customer

    async def list(self, page: int = 1, page_size: int = 20) -> tuple[list[Customer], int]:
        return await self.repo.list_all(page=page, page_size=page_size, order_by="created_at", descending=True)

    async def deactivate(self, id: uuid.UUID, actor_id: uuid.UUID | None = None, ip_address: str | None = None) -> bool:
        customer = await self.repo.get_active(id)
        if not customer:
            return False
        await self.repo.soft_delete(id)
        await audit_log(self.session, "customer", id, "deactivated", actor_id=actor_id, ip_address=ip_address)
        return True
