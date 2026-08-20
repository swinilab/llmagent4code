from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.infrastructure.cache import EntityCache

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class CachedService:
    def __init__(self, cache: EntityCache) -> None:
        self.cache = cache

    async def _cached(
        self,
        entity_type: str,
        entity_id: object,
        schema_type: type[SchemaT],
    ) -> SchemaT | None:
        payload = await self.cache.get_json(entity_type, str(entity_id))
        if payload is None:
            return None
        try:
            return schema_type.model_validate(payload)
        except ValidationError:
            await self.cache.invalidate(entity_type, str(entity_id))
            return None

    async def _store_cached(
        self,
        entity_type: str,
        entity_id: object,
        response: BaseModel,
        version: int,
    ) -> None:
        await self.cache.set_json(
            entity_type,
            str(entity_id),
            response.model_dump(mode="json"),
            version=version,
        )

