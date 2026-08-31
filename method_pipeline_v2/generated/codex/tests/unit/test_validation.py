from copy import deepcopy
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.schemas import (
    CustomerCreate,
    InvoiceCreate,
    OrderCreate,
    PaymentCreate,
    ProductCreate,
)


def valid_customer() -> dict:
    return {
        "name": "Nguyen Van A",
        "address": "123 Nguyen Trai, Hanoi",
        "phone": "+84912345678",
        "bankingDetails": {"accountNumber": "123456", "bankName": "Vietcomank 1"},
        "role": "CUSTOMER",
        "orderHistory": [],
    }


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("name",), "A"),
        (("name",), "A" * 101),
        (("name",), "   "),
        (("name",), "Name_1"),
        (("address",), "1234"),
        (("address",), " " * 5),
        (("phone",), "01234567"),
        (("phone",), "+1234567"),
        (("phone",), "+1234567890123456"),
        (("phone",), "+8401234567"),
        (("bankingDetails", "accountNumber"), "12345"),
        (("bankingDetails", "accountNumber"), "123456A"),
        (("bankingDetails", "bankName"), "A"),
        (("role",), "customer"),
        (("orderHistory",), [str(uuid4())]),
    ],
)
def test_customer_rejects_invalid_equivalence_partitions(path: tuple[str, ...], value: object) -> None:
    body = valid_customer()
    target = body
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValidationError):
        CustomerCreate.model_validate(body)


@pytest.mark.parametrize("name", ["Àn", "O'Connor", "Anne-Marie", "A" * 100])
def test_customer_accepts_name_boundaries_and_unicode(name: str) -> None:
    body = valid_customer()
    body["name"] = name
    assert CustomerCreate.model_validate(body).name == name


@pytest.mark.parametrize("amount", ["0.01", "999999.99", "10.00"])
def test_product_accepts_exact_money_boundaries(amount: str) -> None:
    parsed = ProductCreate.model_validate(
        {"description": "ABC", "price": {"amount": amount, "currency": "USD"}}
    )
    assert format(parsed.price.amount, ".2f") == amount


@pytest.mark.parametrize(
    "amount", ["0.00", "1000000.00", "1", "1.0", "1.000", 1.00, -1, "abc", ""]
)
def test_product_rejects_invalid_amount_classes(amount: object) -> None:
    with pytest.raises(ValidationError):
        ProductCreate.model_validate(
            {"description": "ABC", "price": {"amount": amount, "currency": "USD"}}
        )


@pytest.mark.parametrize("currency", ["US", "XYZ", "usd", ""])
def test_product_rejects_unknown_currency(currency: str) -> None:
    with pytest.raises(ValidationError):
        ProductCreate.model_validate(
            {"description": "ABC", "price": {"amount": "10.00", "currency": currency}}
        )


def test_order_enforces_item_boundaries_uniqueness_and_initial_status() -> None:
    customer_id = str(uuid4())
    product_id = str(uuid4())
    base = {"customerRef": customer_id, "lineItems": [{"productRef": product_id, "quantity": 1}]}
    assert OrderCreate.model_validate(base).status.value == "PLACED"
    for quantity in (0, 1001, -1, 1.5, "1", True):
        body = deepcopy(base)
        body["lineItems"][0]["quantity"] = quantity
        with pytest.raises(ValidationError):
            OrderCreate.model_validate(body)
    duplicate = deepcopy(base)
    duplicate["lineItems"].append(deepcopy(duplicate["lineItems"][0]))
    with pytest.raises(ValidationError):
        OrderCreate.model_validate(duplicate)
    with pytest.raises(ValidationError):
        OrderCreate.model_validate({**base, "status": "SHIPPED"})


@pytest.mark.parametrize(
    ("issue_date", "due_date", "valid"),
    [
        ("29/02/2024", "29/02/2024", True),
        ("31/02/2026", "01/03/2026", False),
        ("23-07-2026", "30/07/2026", False),
        ("23/07/2026", "22/07/2026", False),
        ("30/04/2026", "31/04/2026", False),
    ],
)
def test_invoice_dates_have_lexical_and_calendar_validation(
    issue_date: str, due_date: str, valid: bool
) -> None:
    body = {
        "orderRef": str(uuid4()),
        "billingInfo": {"name": "Valid Name"},
        "issueDate": issue_date,
        "dueDate": due_date,
    }
    if valid:
        assert InvoiceCreate.model_validate(body).issueDate is not None
    else:
        with pytest.raises(ValidationError):
            InvoiceCreate.model_validate(body)


def test_payment_has_strict_amount_method_status_and_uuid() -> None:
    base = {"orderRef": str(uuid4()), "amount": "100.00", "method": "CREDIT_CARD"}
    assert PaymentCreate.model_validate(base).status.value == "PENDING"
    for changes in (
        {"amount": "100.001"},
        {"amount": None},
        {"method": "CASH"},
        {"status": "VERIFIED"},
        {"orderRef": "not-a-uuid"},
    ):
        with pytest.raises(ValidationError):
            PaymentCreate.model_validate({**base, **changes})
