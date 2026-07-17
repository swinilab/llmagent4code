"""Product service for product lookup and inventory management."""

from sqlmodel import Session, select
from typing import List, Optional

from ..models import Product

class ProductService:
    @staticmethod
    def get_product(session: Session, product_id: int) -> Optional[Product]:
        """Retrieve a product by its ID without side‑effects.

        The caller is responsible for any transactional handling. This method
        performs a simple primary‑key lookup.
        """
        return session.get(Product, product_id)

    @staticmethod
    def reduce_stock(session: Session, product_id: int, qty: int) -> None:
        """Atomically decrease the available quantity of a product.

        Uses a row‑level lock when the underlying DB supports it (PostgreSQL,
        MySQL/MariaDB). Raises ``ValueError`` if the product does not exist or
        if there is insufficient stock. The change is persisted by the caller's
        transaction (no commit here).
        """
        # Choose locking strategy based on dialect
        if session.get_bind().dialect.name in {"postgresql", "postgres", "mysql", "mariadb"}:
            stmt = select(Product).where(Product.id == product_id).with_for_update()
        else:
            # SQLite and others: simple select; transaction serialisation will protect writes
            stmt = select(Product).where(Product.id == product_id)
        product = session.exec(stmt).one_or_none()
        if product is None:
            raise ValueError(f"Product {product_id} not found")
        if product.quantity < qty:
            raise ValueError(f"Insufficient stock for product {product_id}")
        product.quantity -= qty
        session.add(product)

    @staticmethod
    def list_products(session: Session) -> List[Product]:
        """Return a list of all products available in the catalog."""
        return session.exec(select(Product)).all()
