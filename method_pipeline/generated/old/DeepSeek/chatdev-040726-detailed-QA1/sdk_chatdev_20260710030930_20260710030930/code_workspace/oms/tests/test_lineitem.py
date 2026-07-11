"""Tests for the LineItem domain model."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.models import LineItem
from uuid import UUID


class TestLineItem:
    """Verify LineItem model creation and validation."""

    def test_total_price_auto_calculation(self):
        """total_price should auto-calculate when not provided."""
        item = LineItem(
            product_id=UUID("00000000-0000-0000-0000-000000000001"),
            product_name="Test Product",
            quantity=3,
            unit_price=Decimal("10.00"),
        )
        assert item.total_price == Decimal("30.00")

    def test_total_price_explicit(self):
        """total_price should accept an explicit value."""
        item = LineItem(
            product_id=UUID("00000000-0000-0000-0000-000000000001"),
            product_name="Test Product",
            quantity=3,
            unit_price=Decimal("10.00"),
            total_price=Decimal("35.00"),
        )
        assert item.total_price == Decimal("35.00")

    def test_quantity_must_be_positive(self):
        """quantity must be >= 1."""
        with pytest.raises(ValidationError):
            LineItem(
                product_id=UUID("00000000-0000-0000-0000-000000000001"),
                product_name="Test Product",
                quantity=0,
                unit_price=Decimal("10.00"),
            )

    def test_quantity_one_is_valid(self):
        """quantity of 1 is valid."""
        item = LineItem(
            product_id=UUID("00000000-0000-0000-0000-000000000001"),
            product_name="Test Product",
            quantity=1,
            unit_price=Decimal("10.00"),
        )
        assert item.quantity == 1
        assert item.total_price == Decimal("10.00")

    def test_zero_unit_price(self):
        """unit_price can be zero (e.g., promotional item)."""
        item = LineItem(
            product_id=UUID("00000000-0000-0000-0000-000000000001"),
            product_name="Free Item",
            quantity=2,
            unit_price=Decimal("0.00"),
        )
        assert item.total_price == Decimal("0.00")

    def test_large_quantity(self):
        """Large quantities should calculate correctly."""
        item = LineItem(
            product_id=UUID("00000000-0000-0000-0000-000000000001"),
            product_name="Bulk Item",
            quantity=1000,
            unit_price=Decimal("0.99"),
        )
        assert item.total_price == Decimal("990.00")

    def test_decimal_precision(self):
        """Decimal precision should be maintained within 2 decimal places."""
        item = LineItem(
            product_id=UUID("00000000-0000-0000-0000-000000000001"),
            product_name="Precise Item",
            quantity=3,
            unit_price=Decimal("10.33"),
        )
        assert item.total_price == Decimal("30.99")
