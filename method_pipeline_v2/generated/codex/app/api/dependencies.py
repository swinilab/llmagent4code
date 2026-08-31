from fastapi import Request

from app.controllers.customer_controller import CustomerController
from app.controllers.invoice_controller import InvoiceController
from app.controllers.order_controller import OrderController
from app.controllers.payment_controller import PaymentController
from app.controllers.product_controller import ProductController
from app.services.customer_service import CustomerService
from app.services.invoice_service import InvoiceService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.product_service import ProductService


def get_customer_controller(request: Request) -> CustomerController:
    return CustomerController(CustomerService(request.app.state.session_factory, request.app.state.cache))


def get_product_controller(request: Request) -> ProductController:
    return ProductController(ProductService(request.app.state.session_factory, request.app.state.cache))


def get_order_controller(request: Request) -> OrderController:
    return OrderController(OrderService(request.app.state.session_factory, request.app.state.cache))


def get_invoice_controller(request: Request) -> InvoiceController:
    return InvoiceController(InvoiceService(request.app.state.session_factory, request.app.state.cache))


def get_payment_controller(request: Request) -> PaymentController:
    return PaymentController(PaymentService(request.app.state.session_factory, request.app.state.cache))

