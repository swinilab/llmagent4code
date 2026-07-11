"""
Tests for the Order Management System services.
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock

from oms.domain.enums import OrderStatus
from oms.domain.models import (
    Customer, Product, Order, OrderLineItem,
)
from oms.domain.errors import EntityNotFoundError
from oms.application.services import (
    CustomerService, ProductService, OrderService, PaymentService, InvoiceService,
)
from oms.application.workflows import WorkflowService


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def mock_cache():
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.delete = AsyncMock()
    cache.delete_pattern = AsyncMock()
    return cache


@pytest.fixture
def mock_task_queue():
    queue = AsyncMock()
    queue.enqueue = AsyncMock(return_value="job-123")
    return queue


@pytest.fixture
def sample_customer():
    return Customer(
        id="c1", name="Alice", address="123 Main St",
        phone="555-0100", banking_details="ACC-001", role="CUSTOMER",
    )


@pytest.fixture
def sample_product():
    return Product(
        id="p1", description="Widget", base_price=Decimal("19.99"), currency="USD",
    )


@pytest.fixture
def sample_order(sample_customer, sample_product):
    item = OrderLineItem(
        product_id=sample_product.id,
        product_description=sample_product.description,
        quantity=2,
        unit_price=sample_product.base_price,
    )
    return Order(
        id="o1", customer_id=sample_customer.id,
        line_items=[item], status=OrderStatus.CREATED,
    )


class TestCustomerService:
    @pytest.mark.asyncio
    async def test_get_customer_found(self, mock_session, sample_customer):
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=sample_customer)
        service = CustomerService(repo)
        result = await service.get_customer(mock_session, "c1")
        assert result.id == "c1"
        assert result.name == "Alice"

    @pytest.mark.asyncio
    async def test_get_customer_not_found(self, mock_session):
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(side_effect=EntityNotFoundError("Customer", "c99"))
        service = CustomerService(repo)
        with pytest.raises(EntityNotFoundError):
            await service.get_customer(mock_session, "c99")


class TestProductService:
    @pytest.mark.asyncio
    async def test_search_products_caches_results(self, mock_session, mock_cache, sample_product):
        repo = AsyncMock()
        repo.search = AsyncMock(return_value=[sample_product])
        service = ProductService(repo, mock_cache)
        results = await service.search_products(mock_session, "widget")
        assert len(results) == 1
        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_product_caches(self, mock_session, mock_cache, sample_product):
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=sample_product)
        service = ProductService(repo, mock_cache)
        result = await service.get_product(mock_session, "p1")
        assert result.id == "p1"
        mock_cache.set.assert_called_once()


class TestOrderService:
    @pytest.mark.asyncio
    async def test_create_order(self, mock_session, sample_order):
        repo = AsyncMock()
        repo.create = AsyncMock(return_value=sample_order)
        service = OrderService(repo)
        result = await service.create_order(mock_session, "c1", [
            {"product_id": "p1", "product_description": "Widget",
             "quantity": 2, "unit_price": Decimal("19.99")},
        ])
        assert result.id == "o1"

    @pytest.mark.asyncio
    async def test_transition_order_valid(self, mock_session, sample_order):
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=sample_order)
        repo.update_status = AsyncMock(return_value=sample_order)
        service = OrderService(repo)
        result = await service.transition_order(
            mock_session, "o1", OrderStatus.ACCEPTED, 1
        )
        assert result is not None


class TestWorkflowService:
    @pytest.mark.asyncio
    async def test_place_order(self, mock_session, mock_cache, mock_task_queue, sample_customer, sample_order):
        customer_repo = AsyncMock()
        customer_repo.get_by_id = AsyncMock(return_value=sample_customer)
        product_repo = AsyncMock()
        order_repo = AsyncMock()
        order_repo.create = AsyncMock(return_value=sample_order)

        customer_svc = CustomerService(customer_repo)
        product_svc = ProductService(product_repo, mock_cache)
        order_svc = OrderService(order_repo)
        payment_svc = PaymentService(AsyncMock())
        invoice_svc = InvoiceService(AsyncMock())

        workflow = WorkflowService(
            customer_svc, product_svc, order_svc,
            payment_svc, invoice_svc, mock_task_queue,
        )

        result = await workflow.place_order(mock_session, "c1", [
            {"product_id": "p1", "product_description": "Widget",
             "quantity": 2, "unit_price": Decimal("19.99")},
        ])
        assert result.id == "o1"
