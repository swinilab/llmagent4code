"""
Shared service utilities: audit logging, code generation, and domain events.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from oms_backend.repositories.entities import AuditLogRepository


async def audit_log(
    session: AsyncSession,
    entity_type: str,
    entity_id: uuid.UUID,
    action: str,
    actor_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    """Append an audit log entry within the current transaction."""
    repo = AuditLogRepository(session)
    await repo.log(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor_id=actor_id,
        payload=payload,
        ip_address=ip_address,
    )


def build_billing_address(customer) -> str:
    parts = []
    if customer.address_line1:
        parts.append(customer.address_line1)
    if customer.address_line2:
        parts.append(customer.address_line2)
    city_state = []
    if customer.city:
        city_state.append(customer.city)
    if customer.state:
        city_state.append(customer.state)
    if city_state:
        parts.append(", ".join(city_state))
    if customer.postal_code:
        parts.append(customer.postal_code)
    if customer.country:
        parts.append(customer.country)
    return "\n".join(parts)
