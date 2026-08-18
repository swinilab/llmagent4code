"""
Base repository with caching and retry logic
Implements NFR 1.2 (caching), NFR 2.2 (graceful degradation), NFR 2.3 (resynchronization)
"""
from typing import Generic, TypeVar, Optional, List, Any, Dict
from uuid import UUID
from sqlalchemy.orm import Session
from oms_backend.utils.cache import cache_manager
from oms_backend.utils.retry import execute_with_retry, synchronize_state
from oms_backend.config import settings

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Base repository with caching and retry logic.
    Satisfies:
    - NFR 1.2: Maintain Multiple copies of Data (caching)
    - NFR 2.2: Graceful Degradation (fallback on cache miss)
    - NFR 2.3: State Resynchronization (periodic sync between cache and DB)
    """
    
    def __init__(self, session: Session, model_class: type, cache_prefix: str):
        """
        Initialize base repository.
        
        Args:
            session: Database session
            model_class: SQLAlchemy model class
            cache_prefix: Prefix for cache keys
        """
        self.session = session
        self.model_class = model_class
        self.cache_prefix = cache_prefix
        
    def _get_cache_key(self, id: UUID) -> str:
        """Generate cache key for an entity"""
        return f"{self.cache_prefix}:{id}"
    
    def _get_all_cache_key(self) -> str:
        """Generate cache key for all entities"""
        return f"{self.cache_prefix}:all"
    
    def get_by_id(self, id: UUID) -> Optional[Any]:
        """
        Get entity by ID with caching.
        NFR 1.2: Cache lookup before database query.
        
        Args:
            id: Entity ID
            
        Returns:
            Entity or None if not found
        """
        # Try cache first (NFR 1.2)
        cached = cache_manager.get(self._get_cache_key(id))
        if cached is not None:
            return cached
        
        # Fallback to database (NFR 2.2: Graceful Degradation)
        entity = self.session.get(self.model_class, id)
        if entity:
            # Cache the result
            cache_manager.set(self._get_cache_key(id), self._to_dict(entity))
        return entity
    
    def get_all(self) -> List[Any]:
        """
        Get all entities with caching.
        
        Returns:
            List of entities
        """
        # Try cache first
        cached = cache_manager.get(self._get_all_cache_key())
        if cached is not None:
            return cached
        
        # Fallback to database
        entities = self.session.query(self.model_class).all()
        result = [self._to_dict(e) for e in entities]
        cache_manager.set(self._get_all_cache_key(), result)
        return result
    
    def create(self, entity_data: Dict[str, Any]) -> Any:
        """
        Create entity with cache invalidation.
        
        Args:
            entity_data: Entity data
            
        Returns:
            Created entity
        """
        entity = self.model_class(**entity_data)
        self.session.add(entity)
        self.session.flush()  # Get generated ID
        self.session.refresh(entity)
        
        # Invalidate "all" cache
        cache_manager.delete(self._get_all_cache_key())
        
        return entity
    
    def update(self, id: UUID, entity_data: Dict[str, Any]) -> Optional[Any]:
        """
        Update entity with cache invalidation.
        
        Args:
            id: Entity ID
            entity_data: Updated data
            
        Returns:
            Updated entity or None if not found
        """
        entity = self.get_by_id(id)
        if not entity:
            return None
        
        for key, value in entity_data.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        
        self.session.flush()
        self.session.refresh(entity)
        
        # Invalidate caches
        cache_manager.delete(self._get_cache_key(id))
        cache_manager.delete(self._get_all_cache_key())
        
        return entity
    
    def delete(self, id: UUID) -> bool:
        """
        Delete entity with cache invalidation.
        
        Args:
            id: Entity ID
            
        Returns:
            True if deleted, False if not found
        """
        entity = self.get_by_id(id)
        if not entity:
            return False
        
        self.session.delete(entity)
        
        # Invalidate caches
        cache_manager.delete(self._get_cache_key(id))
        cache_manager.delete(self._get_all_cache_key())
        
        return True
    
    def _to_dict(self, entity: Any) -> Dict[str, Any]:
        """Convert SQLAlchemy entity to dictionary"""
        return {c.name: getattr(entity, c.name) for c in entity.__table__.columns}
    
    def resynchronize(self, id: UUID) -> bool:
        """
        Resynchronize cache with database.
        NFR 2.3: State Resynchronization - compare and sync states.
        
        Args:
            id: Entity ID
            
        Returns:
            True if synchronized, False otherwise
        """
        db_entity = self.session.get(self.model_class, id)
        if not db_entity:
            return False
        
        cached = cache_manager.get(self._get_cache_key(id))
        
        def compare(db, cache):
            return db == cache
        
        def sync(db):
            cache_manager.set(self._get_cache_key(id), self._to_dict(db))
            return self._to_dict(db)
        
        return synchronize_state(
            self._to_dict(db_entity),
            cached,
            compare,
            sync
        )
