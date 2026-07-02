"""
Base repository with common CRUD operations.

Provides async database operations using SQLAlchemy 2.0 async session.
"""
from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Generic base repository providing common CRUD operations.
    
    This class implements the repository pattern for data access abstraction,
    providing async operations for all database interactions.
    """
    
    def __init__(self, model: Type[T], session: AsyncSession):
        """
        Initialize the repository with a model class and session.
        
        Args:
            model: SQLAlchemy model class
            session: Async SQLAlchemy session
        """
        self.model = model
        self.session = session
    
    async def get(self, entity_id: int) -> Optional[T]:
        """
        Get an entity by ID.
        
        Args:
            entity_id: Primary key ID
            
        Returns:
            Entity instance or None if not found
        """
        result = await self.session.get(self.model, entity_id)
        return result
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """
        Get all entities with pagination.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of entity instances
        """
        query = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def count(self) -> int:
        """
        Count total number of entities.
        
        Returns:
            Total count of entities
        """
        query = select(func.count()).select_from(self.model)
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def create(self, entity: T) -> T:
        """
        Create a new entity.
        
        Args:
            entity: Entity instance to create
            
        Returns:
            Created entity instance
        """
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
    
    async def update(self, entity: T) -> T:
        """
        Update an existing entity.
        
        Args:
            entity: Entity instance with updated values
            
        Returns:
            Updated entity instance
        """
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
    
    async def delete(self, entity_id: int) -> bool:
        """
        Delete an entity by ID.
        
        Args:
            entity_id: Primary key ID
            
        Returns:
            True if deleted, False if not found
        """
        entity = await self.get(entity_id)
        if entity is None:
            return False
        await self.session.delete(entity)
        await self.session.flush()
        return True
    
    async def delete_all(self) -> int:
        """
        Delete all entities.
        
        Returns:
            Number of deleted entities
        """
        query = delete(self.model)
        result = await self.session.execute(query)
        await self.session.flush()
        return result.rowcount or 0
