"""
OMS Unit Tests - Services
Tests for customer, order, product, payment, and invoice services.
"""
import pytest
from decimal import Decimal

from app.service_layer.services.customer_service import CustomerService
from app.service_layer.services.order_service import OrderService
from app.service_layer.services.product_service import ProductService
from app.service_layer.services.payment_service import PaymentService
from app.service_layer.services.invoice_service import InvoiceService
from app.domain.entities.models import (
    OrderStatus, PaymentStatus, InvoiceStatus, PaymentMethod, Currency
)


class TestCustomerService:
    """Tests for CustomerService."""

    def test_create_customer(self, customer_repo):
        """Creating a customer should persist and return the customer."""
        service = CustomerService(customer_repo)

        customer = service.create_customer(
            name="John Doe",
            email="john@example.com",
            phone="+1234567890"
        )

        assert customer.id is not None
        assert customer.name == "John Doe"
        assert customer.email == "john@example.com"

    def test_create_duplicate_email_fails(self, customer_repo):
        """Creating a customer with existing email should fail."""
        service = CustomerService(customer_repo)

        service.create_customer(name="John", email="john@example.com")

        with pytest.raises(ValueError, match="already exists"):
            service.create_customer(name="Jane", email="john@example.com")

    def test_get_customer(self, customer_repo, sample_customer):
        """Getting a customer by ID should return the customer."""
        service = CustomerService(customer_repo)
        saved = customer_repo.save(sample_customer)

        result = service.get_customer(saved.id)

        assert result is not None
        assert result.id == saved.id
        assert result.email == saved.email

    def test_update_customer(self, customer_repo, sample_customer):
        """Updating a customer should modify and return the updated customer."""
        service = CustomerService(customer_repo)
        saved = customer_repo.save(sample_customer)

        result = service.update_customer(saved.id, {"name": "Updated Name"})

        assert result is not None
        assert result.name == "Updated Name"

    def test_list_customers_by_role(self, customer_repo, sample_customer):
        """Listing customers by role should return matching customers."""
        customer_repo.save(sample_customer)

        service = CustomerService(customer_repo)
        customers = service.list_customers_by_role(sample_customer.role)

        assert len(customers) >= 1
        assert any(c.email == sample_customer.email for c in customers)


class TestProductService:
    """Tests for ProductService."""

    def test_create_product(self, product_repo):
        """Creating a product should persist and return the product."""
        service = ProductService(product_repo)

        product = service.create_product(
            sku="LAPTOP-001",
            name="Test Laptop",
            price_amount="999.99",
            stock_quantity=10
        )

        assert product.id is not None
        assert product.sku == "LAPTOP-001"
        assert product.stock_quantity == 10

    def test_create_duplicate_sku_fails(self, product_repo):
        """Creating a product with existing SKU should fail."""
        service = ProductService(product_repo)

        service.create_product(sku="LAPTOP-001", name="Laptop", price_amount="999.99")

        with pytest.raises(ValueError, match="already exists"):
            service.create_product(sku="LAPTOP-001", name="Another Laptop", price_amount="899.99")

    def test_search_products(self, product_repo, sample_product):
        """Searching products should return matching products."""
        product_repo.save(sample_product)

        service = ProductService(product_repo)
        results = service.search_products("Laptop")

        assert len(results) >= 1

    def test_update_stock(self, product_repo, sample_product):
        """Updating stock should modify the quantity."""
        product_repo.save(sample_product)

        service = ProductService(product_repo)
        result = service.update_stock(sample_product.id, 5)

        assert result is not None
        assert result.stock_quantity == 5

    def test_reserve_and_release_stock(self, product_repo, sample_product):
        """Reserving and releasing stock should update quantities correctly."""
        product_repo.save(sample_product)

        service = ProductService(product_repo)
        
        reserved = service.reserve_stock(sample_product.id, 3)
        assert reserved is True
        
        product = product_repo.find_by_id(sample_product.id)
        assert product.stock_quantity == 7

        released = service.release_stock(sample_product.id, 3)
        assert released is True
        
        product = product_repo.find_by_id(sample_product.id)
        assert product.stock_quantity == 10

    def test_create_order(self, product_repo, sample_product):
        """Creating an order should reserve stock."""
        product_repo.save(sample_product)

        service = ProductService(product_repo)
        reserved = service.reserve_stock(sample_product.id, 1)

        assert reserved is True
        product = product_repo.find_by_id(sample_product.id)
        assert product.stock_quantity == 9


class TestOrderService:
    """Tests for OrderService."""

    def test_create_order(self, order_repo, product_repo, sample_order, sample_product):
        """Creating an order should persist and return the order."""
        product_repo.save(sample_product)
        
        service = OrderService(order_repo, product_repo)
        order = service.create_order(
            customer_id=sample_order.customer_id,
            line_items=sample_order.line_items,
            shipping_address=sample_order.shipping_address
        )

        assert order.id is not None
        assert order.status == OrderStatus.PENDING

    def test_accept_order(self, order_repo, sample_order):
        """Accepting an order should update its status."""
        order_repo.save(sample_order)

        service = OrderService(order_repo, None)
        result = service.accept_order(sample_order.id)

        assert result is not None
        assert result.status == OrderStatus.ACCEPTED

    def test_reject_order(self, order_repo, sample_order):
        """Rejecting an order should update its status."""
        order_repo.save(sample_order)

        service = OrderService(order_repo, None)
        result = service.reject_order(sample_order.id)

        assert result is not None
        assert result.status == OrderStatus.REJECTED

    def test_order_lifecycle(self, order_repo, product_repo, sample_order, sample_product):
        """Order should transition through full lifecycle."""
        product_repo.save(sample_product)
        order_repo.save(sample_order)

        service = OrderService(order_repo, product_repo)
        
        order = service.accept_order(sample_order.id)
        assert order.status == OrderStatus.ACCEPTED
        
        order = service.ship_order(order.id)
        assert order.status == OrderStatus.SHIPPED
        
        order = service.complete_order(order.id)
        assert order.status == OrderStatus.COMPLETED


class TestPaymentService:
    """Tests for PaymentService."""

    def test_create_payment(self, payment_repo, sample_order, sample_customer):
        """Creating a payment should persist and return the payment."""
        service = PaymentService(payment_repo)

        payment = service.create_payment(
            order_id=sample_order.id,
            customer_id=sample_customer.id,
            amount=sample_order.total,
            method=PaymentMethod.BANK_TRANSFER
        )

        assert payment.id is not None
        assert payment.status == PaymentStatus.PENDING

    def test_complete_payment(self, payment_repo, sample_order, sample_customer):
        """Completing a payment should update its status."""
        service = PaymentService(payment_repo)

        payment = service.create_payment(
            order_id=sample_order.id,
            customer_id=sample_customer.id,
            amount=sample_order.total,
            method=PaymentMethod.BANK_TRANSFER
        )

        result = service.complete_payment(payment.id, "TXN-123")

        assert result is not None
        assert result.status == PaymentStatus.COMPLETED

    def test_fail_payment(self, payment_repo, sample_order, sample_customer):
        """Failing a payment should update its status."""
        service = PaymentService(payment_repo)

        payment = service.create_payment(
            order_id=sample_order.id,
            customer_id=sample_customer.id,
            amount=sample_order.total,
            method=PaymentMethod.BANK_TRANSFER
        )

        result = service.fail_payment(payment.id, "Insufficient funds")

        assert result is not None
        assert result.status == PaymentStatus.FAILED


class TestInvoiceService:
    """Tests for InvoiceService."""

    def test_create_invoice(self, invoice_repo, sample_order, sample_customer):
        """Creating an invoice should persist and return the invoice."""
        service = InvoiceService(invoice_repo)

        invoice = service.create_invoice(
            order_id=sample_order.id,
            customer_id=sample_customer.id,
            line_items=sample_order.line_items,
            subtotal=sample_order.subtotal,
            tax_total=sample_order.tax_total,
            discount_total=sample_order.discount_total,
            total=sample_order.total
        )

        assert invoice.id is not None
        assert invoice.invoice_number is not None

    def test_issue_invoice(self, invoice_repo, sample_order, sample_customer):
        """Issuing an invoice should update its status."""
        service = InvoiceService(invoice_repo)

        invoice = service.create_invoice(
            order_id=sample_order.id,
            customer_id=sample_customer.id,
            line_items=sample_order.line_items,
            subtotal=sample_order.subtotal,
            tax_total=sample_order.tax_total,
            discount_total=sample_order.discount_total,
            total=sample_order.total
        )

        result = service.issue_invoice(invoice.id)

        assert result is not None
        assert result.status == InvoiceStatus.ISSUED

    def test_mark_invoice_paid(self, invoice_repo, sample_order, sample_customer):
        """Marking an invoice as paid should update its status."""
        service = InvoiceService(invoice_repo)

        invoice = service.create_invoice(
            order_id=sample_order.id,
            customer_id=sample_customer.id,
            line_items=sample_order.line_items,
            subtotal=sample_order.subtotal,
            tax_total=sample_order.tax_total,
            discount_total=sample_order.discount_total,
            total=sample_order.total
        )

        issued = service.issue_invoice(invoice.id)
        result = service.mark_invoice_paid(issued.id, "PAY-123")

        assert result is not None
        assert result.status == InvoiceStatus.PAID

    def test_invoice_number_generation(self, invoice_repo, sample_order, sample_customer):
        """Invoice numbers should be unique and sequential."""
        service = InvoiceService(invoice_repo)

        invoice1 = service.create_invoice(
            order_id=sample_order.id,
            customer_id=sample_customer.id,
            line_items=sample_order.line_items,
            subtotal=sample_order.subtotal,
            tax_total=sample_order.tax_total,
            discount_total=sample_order.discount_total,
            total=sample_order.total
        )

        invoice2 = service.create_invoice(
            order_id="order-002",
            customer_id=sample_customer.id,
            line_items=sample_order.line_items,
            subtotal=sample_order.subtotal,
            tax_total=sample_order.tax_total,
            discount_total=sample_order.discount_total,
            total=sample_order.total
        )

        assert invoice1.invoice_number != invoice2.invoice_number
