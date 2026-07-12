"""
OMS Core Configuration - Application configuration and service registry.
"""
from __future__ import annotations
import threading
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class AppConfig:
    """Application configuration."""
    database__path: str = "oms.db"
    database__pool_size: int = 10
    database__timeout: float = 30.0
    rate_limiter__enabled: bool = True
    rate_limiter__max_requests: int = 100
    rate_limiter__window_seconds: float = 60.0
    circuit_breaker__enabled: bool = True
    circuit_breaker__failure_threshold: int = 5
    circuit_breaker__recovery_timeout: float = 30.0
    debug: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AppConfig:
        """Create config from dictionary."""
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


class ServiceRegistry:
    """Service registry for dependency injection."""
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_config'):
            self._config: Optional[AppConfig] = None
            self._db_manager = None
            self._repositories: Dict[str, Any] = {}
    
    def configure(self, config: AppConfig):
        """Configure the service registry."""
        with self._lock:
            self._config = config
            self._db_manager = None
            self._repositories = {}
            self._initialized = True
    
    def _setup_repositories(self):
        """Set up repositories with database manager."""
        if self._db_manager is None:
            return
        
        from app.adapters.persistence import (
            InMemoryCustomerRepository,
            InMemoryProductRepository,
            InMemoryOrderRepository,
            InMemoryPaymentRepository,
            InMemoryInvoiceRepository
        )
        
        self._repositories['customer'] = InMemoryCustomerRepository(self._db_manager)
        self._repositories['product'] = InMemoryProductRepository(self._db_manager)
        self._repositories['order'] = InMemoryOrderRepository(self._db_manager)
        self._repositories['payment'] = InMemoryPaymentRepository(self._db_manager)
        self._repositories['invoice'] = InMemoryInvoiceRepository(self._db_manager)
    
    def get_customer_repo(self):
        """Get customer repository."""
        return self._repositories.get('customer')
    
    def get_product_repo(self):
        """Get product repository."""
        return self._repositories.get('product')
    
    def get_order_repo(self):
        """Get order repository."""
        return self._repositories.get('order')
    
    def get_payment_repo(self):
        """Get payment repository."""
        return self._repositories.get('payment')
    
    def get_invoice_repo(self):
        """Get invoice repository."""
        return self._repositories.get('invoice')
    
    def reset(self):
        """Reset the service registry."""
        with self._lock:
            self._config = None
            if self._db_manager:
                self._db_manager.close_connection()
                self._db_manager = None
            self._repositories = {}
            self._initialized = False


_config: Optional[AppConfig] = None


def configure_app(config: AppConfig):
    """Configure the application."""
    global _config
    _config = config
    ServiceRegistry().configure(config)


def get_config() -> Optional[AppConfig]:
    """Get the current configuration."""
    return _config
