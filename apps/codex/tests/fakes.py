from __future__ import annotations

from copy import deepcopy
from typing import Any


class FakeCache:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], dict[str, Any]] = {}

    async def get_json(self, entity_type: str, entity_id: object) -> dict[str, Any] | None:
        value = self.values.get((entity_type, str(entity_id)))
        return deepcopy(value) if value is not None else None

    async def set_json(
        self,
        entity_type: str,
        entity_id: object,
        payload: dict[str, Any],
        *,
        version: int | str | None = None,
    ) -> bool:
        self.values[(entity_type, str(entity_id))] = deepcopy(payload)
        return True

    async def invalidate(self, entity_type: str, entity_id: object) -> bool:
        self.values.pop((entity_type, str(entity_id)), None)
        return True

