"""
Product service layer
Business logic for product operations
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from oms_backend.repository import ProductRepository
from oms_backend.repository.models import ProductModel
from oms_backend.domain.models import Product, ProductCreate
from oms_backend.utils.exceptions import NotFoundException


class ProductService:
    """
    Service for product operations.
    Handles business logic and transaction boundaries.
    """
    
    def __init__(self, session: Session):
        """
        Initialize product service.
        
        Args:
            session: Database session
        """
        self.session = session
        self.repository = ProductRepository(session)
    
    def get_product(self, product_id: UUID) -> Product:
        """
        Get product by ID.
        
        Args:
            product_id: Product ID
            
        Returns:
            Product object
            
        Raises:
            NotFoundException: If product not found
        """
        model = self.repository.find_by_id(product_id)
        if not model:
            raise NotFoundException("Product", str(product_id))
        return self._to_domain(model)
    
    def get_all_products(self) -> List[Product]:
        """
        Get all products.
        
        Returns:
            List of products
        """
        models = self.repository.find_all()
        return [self._to_domain(m) for m in models]
    
    def create_product(self, data: ProductCreate) -> Product:
        """
        Create a new product.
        
        Args:
            data: Product creation data
            
        Returns:
            Created product
        """
        model_data = {
            "description": data.description,
            "price_amount": Decimal(data.price.amount),
            "price_currency": data.price.currency,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        model = self.repository.create_product(model_data)
        self.session.commit()
        return self._to_domain(model)
    
    def update_product(self, product_id: UUID, data: Dict[str, Any]) -> Product:
        """
        Update product.
        
        Args:
            product_id: Product ID
            data: Update data
            
        Returns:
            Updated product
            
        Raises:
            NotFoundException: If product not found
        """
        if "price" in data and isinstance(data["price"], dict):
            if "amount" in data["price"]:
                data["price_amount"] = Decimal(data["price"]["amount"])
            if "currency" in data["price"]:
                data["price_currency"] = data["price"]["currency"]
            del data["price"]
        
        model = self.repository.update_product(product_id, {
            **data,
            "updated_at": datetime.utcnow()
        })
        if not model:
            raise NotFoundException("Product", str(product_id))
        self.session.commit()
        return self._to_domain(model)
    
    def delete_product(self, product_id: UUID) -> bool:
        """
        Delete product.
        
        Args:
            product_id: Product ID
            
        Returns:
            True if deleted
            
        Raises:
            NotFoundException: If product not found
        """
        if not self.repository.delete_product(product_id):
            raise NotFoundException("Product", str(product_id))
        self.session.commit()
        return True
    
    def _to_domain(self, model: ProductModel) -> Product:
        """Convert database model to domain model"""
        return Product(
            id=model.id,
            description=model.description,
            price={
                "amount": f"{model.price_amount:.2f}",
                "currency": model.price_currency,
            },
            createdAt=model.created_at,
            updatedAt=model.updated_at,
        )
