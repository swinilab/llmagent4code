from datetime import UTC, datetime, timedelta

from app.domain.schemas import CustomerCreate, InvoiceCreate, OrderCreate, PaymentCreate, ProductCreate
from app.services.customer_service import CustomerService
from app.services.invoice_service import InvoiceService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.product_service import ProductService


async def test_complete_order_to_closure_workflow(session_factory, cache) -> None:
    customers = CustomerService(session_factory, cache)
    products = ProductService(session_factory, cache)
    orders = OrderService(session_factory, cache)
    invoices = InvoiceService(session_factory, cache)
    payments = PaymentService(session_factory, cache)

    customer = await customers.create(
        CustomerCreate.model_validate(
            {
                "name": "Nguyen Van A",
                "address": "123 Nguyen Trai, Hanoi",
                "phone": "+84912345678",
                "bankingDetails": {"accountNumber": "1234567890", "bankName": "Vietcombank"},
                "role": "CUSTOMER",
                "orderHistory": [],
            }
        )
    )
    product = await products.create(
        ProductCreate.model_validate(
            {"description": "Wireless Mouse", "price": {"amount": "100.00", "currency": "USD"}}
        )
    )
    order = await orders.create(
        OrderCreate.model_validate(
            {
                "customerRef": str(customer.id),
                "lineItems": [{"productRef": str(product.id), "quantity": 1}],
            }
        )
    )
    assert order.status.value == "PLACED"
    assert order.totalAmount == product.price.amount
    assert (await customers.get(customer.id)).orderHistory == [order.id]

    accepted = await orders.accept(order.id)
    assert accepted.order.status.value == "ACCEPTED"
    issue = datetime.now(UTC).date()
    invoice = await invoices.create(
        InvoiceCreate.model_validate(
            {
                "orderRef": str(order.id),
                "billingInfo": {"name": customer.name},
                "issueDate": issue.strftime("%d/%m/%Y"),
                "dueDate": (issue + timedelta(days=7)).strftime("%d/%m/%Y"),
            }
        )
    )
    assert invoice.totalAmount == order.totalAmount
    assert (await orders.get(order.id)).invoiceRef == invoice.id

    payment = await payments.create(
        PaymentCreate.model_validate(
            {
                "orderRef": str(order.id),
                "amount": format(invoice.totalAmount, ".2f"),
                "method": "BANK_TRANSFER",
            }
        )
    )
    assert payment.status.value == "PENDING"
    verified = await payments.verify(payment.id)
    assert verified.payment.status.value == "VERIFIED"
    assert verified.invoice.status.value == "PAID"
    assert verified.order.status.value == "VERIFIED"
    assert (await orders.ship(order.id)).order.status.value == "SHIPPED"
    assert (await orders.close(order.id)).order.status.value == "CLOSED"

