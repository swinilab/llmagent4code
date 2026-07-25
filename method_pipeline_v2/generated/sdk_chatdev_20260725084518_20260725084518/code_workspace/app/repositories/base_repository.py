"""
Base repository with common CRUD operations
"""
from typing import TypeVar, Generic, List, Optional, Type, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import DeclarativeBase

T = TypeVar("T", bound=DeclarativeBase)


class BaseRepository(Generic[T]):
    """Base repository with common database operations"""
    
    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model
    
    async def get(self, id: str) -> Optional[T]:
        """Get entity by ID"""
        result = await self.session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()
    
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """List all entities with pagination"""
        result = await self.session.execute(
            select(self.model).offset(offset).limit(limit)
        )
        return list(result.scalars().all())
    
    async def create(self, entity: T) -> T:
        """Create new entity"""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
    
    async def update(self, id: str, **kwargs) -> Optional[T]:
        """Update entity by ID"""
        await self.session.execute(
            update(self.model).where(self.model.id == id).values(**kwargs)
        )
        return await self.get(id)
    
    async def delete(self, id: str) -> bool:
        """Delete entity by ID"""
        result = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        return result.rowcount > 0
    
    async def count(self) -> int:
        """Count total entities"""
        from sqlalchemy import func
        result = await self.session.execute(select(func.count()).select_from(self.model))
        return result.scalar()
