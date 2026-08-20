from datetime import UTC, datetime
from typing import Any

from app.db.models import (
    CustomerModel,
    InvoiceModel,
    OrderModel,
    PaymentModel,
    ProductModel,
)
from app.domain.schemas import (
    BankingDetails,
    BillingInfo,
    CustomerResponse,
    InvoiceResponse,
    OrderLineItemResponse,
    OrderResponse,
    PaymentResponse,
    Price,
    ProductResponse,
)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def customer_response(customer: CustomerModel, order_history: list[Any]) -> CustomerResponse:
    return CustomerResponse(
        id=customer.id,
        name=customer.name,
        address=customer.address,
        phone=customer.phone,
        bankingDetails=BankingDetails(
            accountNumber=customer.account_number,
            bankName=customer.bank_name,
        ),
        role=customer.role,
        orderHistory=order_history,
    )


def product_response(product: ProductModel) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        description=product.description,
        price=Price(amount=product.price_amount, currency=product.price_currency),
    )


def order_response(order: OrderModel) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        customerRef=order.customer_id,
        lineItems=[
            OrderLineItemResponse(
                productRef=item.product_id,
                quantity=item.quantity,
                unitPriceSnapshot=item.unit_price_snapshot,
            )
            for item in order.items
        ],
        totalAmount=order.total_amount,
        status=order.status,
        createdAt=_aware(order.created_at),
        updatedAt=_aware(order.updated_at),
        invoiceRef=order.invoice_id,
    )


def payment_response(payment: PaymentModel) -> PaymentResponse:
    return PaymentResponse(
        id=payment.id,
        orderRef=payment.order_id,
        amount=payment.amount,
        timestamp=_aware(payment.timestamp),
        status=payment.status,
        method=payment.method,
    )


def invoice_response(invoice: InvoiceModel) -> InvoiceResponse:
    return InvoiceResponse(
        id=invoice.id,
        orderRef=invoice.order_id,
        billingInfo=BillingInfo(
            name=invoice.billing_name,
            address=invoice.billing_address,
        ),
        totalAmount=invoice.total_amount,
        issueDate=invoice.issue_date,
        dueDate=invoice.due_date,
        status=invoice.status,
    )


def serialize_customer_snapshot(customer: CustomerModel) -> dict[str, Any]:
    return customer_response(customer, []).model_dump(mode="json")


def serialize_product_snapshot(product: ProductModel) -> dict[str, Any]:
    return product_response(product).model_dump(mode="json")


def serialize_order_snapshot(order: OrderModel) -> dict[str, Any]:
    return order_response(order).model_dump(mode="json")


def serialize_invoice_snapshot(invoice: InvoiceModel) -> dict[str, Any]:
    return invoice_response(invoice).model_dump(mode="json")


def serialize_payment_snapshot(payment: PaymentModel) -> dict[str, Any]:
    return payment_response(payment).model_dump(mode="json")
