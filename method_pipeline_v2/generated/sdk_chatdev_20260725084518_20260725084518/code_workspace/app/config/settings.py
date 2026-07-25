"""
Application settings and configuration
"""
from pydantic import BaseModel


class Settings(BaseModel):
    """Application configuration settings"""
    
    database_url: str = "sqlite+aiosqlite:///./oms.db"
    host: str = "0.0.0.0"
    port: int = 8000
    max_queue_size: int = 1000
    worker_count: int = 4
    retry_max_attempts: int = 3
    retry_delay_seconds: float = 1.0
    health_check_interval: float = 5.0
    supported_currencies: list = ["USD", "VND", "EUR"]
    max_order_items: int = 100
    max_item_quantity: int = 1000
    
    class Config:
        frozen = True
