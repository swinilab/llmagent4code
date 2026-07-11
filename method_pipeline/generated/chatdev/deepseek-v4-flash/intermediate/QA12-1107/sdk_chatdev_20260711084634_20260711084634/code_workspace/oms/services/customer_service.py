"""
Customer service: customer management operations.

Customer lookups are on the latency-critical checkout path (NFR 1.1).
Uses cache-aside for fast reads.
"""
from __future__ import annotations

import logging
from typing import Optional

from oms.adapters.repositories import CustomerRepository
from oms.domain.models import Address, BankingDetails, Customer
from oms.infrastructure.database import get_session, get_readonly_session

logger = logging.getLogger(__name__)

_customer_repo = CustomerRepository()


class CustomerService:
    """Business logic for customer operations."""

    async def get_customer(self, customer_id: str) -> Customer:
        """Get a customer by ID (cache-aside, latency-critical)."""
        async with get_readonly_session() as session:
            return await _customer_repo.get_by_id(session, customer_id)

    async def create_customer(
        self,
        name: str,
        phone: str = "",
        address: Optional[dict] = None,
        banking_details: Optional[dict] = None,
    ) -> Customer:
        """Create a new customer."""
        async with get_session() as session:
            customer = Customer(
                name=name,
                phone=phone,
                address=Address(**address) if address else None,
                banking_details=BankingDetails(**banking_details)
                if banking_details else None,
            )
            await _customer_repo.save(session, customer)
            logger.info("Customer %s created: %s", customer.id, name)
            return customer

    async def update_customer(
        self,
        customer_id: str,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[dict] = None,
    ) -> Customer:
        """Update an existing customer."""
        async with get_session() as session:
            customer = await _customer_repo.get_by_id(session, customer_id)
            if name is not None:
                customer.name = name
            if phone is not None:
                customer.phone = phone
            if address is not None:
                customer.address = Address(**address)
            await _customer_repo.update(session, customer)
            logger.info("Customer %s updated", customer_id)
            return customer
