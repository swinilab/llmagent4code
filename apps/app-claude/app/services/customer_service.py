"""Customer service.

Customers are not served from a maintained copy: `orderHistory` is derived from
Order state that advances through the workflow, so a stale copy would misreport
workflow progress.
"""

from __future__ import annotations

import uuid

from app.core.errors import NotFoundError
from app.persistence.database import run_with_resilience, session_scope
from app.persistence.models import Customer
from app.persistence.repositories import CustomerRepository
from app.schemas.dto import CustomerCreateRequest, CustomerResponse, customer_to_response


def create_customer(payload: CustomerCreateRequest) -> CustomerResponse:
    def operation() -> CustomerResponse:
        with session_scope() as session:
            customer = Customer(
                name=payload.name,
                address=payload.address,
                phone=payload.phone,
                bank_account_number=payload.bankingDetails.accountNumber,
                bank_name=payload.bankingDetails.bankName,
                role=payload.role.value,
            )
            CustomerRepository(session).add(customer)
            return customer_to_response(customer, [])

    return run_with_resilience(operation, operation_name="customer.create", retryable=False)


def get_customer(customer_id: uuid.UUID) -> CustomerResponse:
    def operation() -> CustomerResponse | None:
        with session_scope() as session:
            repository = CustomerRepository(session)
            customer = repository.get(customer_id)
            if customer is None:
                return None
            return customer_to_response(customer, repository.order_ids(customer_id))

    result = run_with_resilience(operation, operation_name="customer.get")
    if result is None:
        raise NotFoundError(f"Customer {customer_id} was not found")
    return result
