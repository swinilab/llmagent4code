from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.resilience import DependencyTimeoutError, run_with_timeout
from app.core.observability import RESYNC_MISMATCHES
from app.infrastructure.cache import EntityCache


logger = logging.getLogger(__name__)

SnapshotSerializer = Callable[[Any], Mapping[str, Any]]
VersionReader = Callable[[Any], int | str | None]
RowPredicate = Callable[[Any], bool]


@dataclass(frozen=True, slots=True)
class EntitySyncSpec:
    entity_type: str
    model: type[Any]
    serializer: SnapshotSerializer
    version_reader: VersionReader = lambda row: getattr(row, "version", None)
    include: RowPredicate = lambda row: getattr(row, "deleted_at", None) is None


@dataclass(frozen=True, slots=True)
class StateSyncReport:
    compared: int = 0
    repaired: int = 0
    removed: int = 0
    errors: int = 0


class StateSynchronizer:
    """Periodically compare canonical rows with Redis and repair secondary drift."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        cache: EntityCache,
        specs: Iterable[EntitySyncSpec],
        *,
        interval_seconds: float,
        dependency_timeout_seconds: float,
        batch_size: int = 500,
    ) -> None:
        self._session_factory = session_factory
        self._cache = cache
        self._specs = tuple(specs)
        self._interval_seconds = interval_seconds
        self._dependency_timeout_seconds = dependency_timeout_seconds
        self._batch_size = batch_size
        if interval_seconds <= 0 or dependency_timeout_seconds <= 0 or batch_size <= 0:
            raise ValueError("synchronizer timing and batch size must be greater than zero")
        if not self._specs:
            raise ValueError("at least one entity synchronization spec is required")
        entity_types = [spec.entity_type for spec in self._specs]
        if len(entity_types) != len(set(entity_types)):
            raise ValueError("entity synchronization types must be unique")
        self._run_lock = asyncio.Lock()

    async def resynchronize_once(self) -> StateSyncReport:
        """Compare active PostgreSQL state with standby Redis snapshots once."""

        compared = repaired = removed = errors = 0
        async with self._run_lock:
            try:
                async with self._session_factory() as session:
                    for spec in self._specs:
                        canonical_ids: set[str] = set()
                        canonical_scan_complete = True
                        offset = 0
                        while True:
                            statement = (
                                select(spec.model)
                                .order_by(spec.model.id)
                                .offset(offset)
                                .limit(self._batch_size)
                            )
                            try:
                                result = await run_with_timeout(
                                    session.execute(statement),
                                    self._dependency_timeout_seconds,
                                    dependency=f"postgresql {spec.entity_type} snapshot",
                                )
                            except (DependencyTimeoutError, SQLAlchemyError):
                                logger.exception(
                                    "canonical snapshot read failed",
                                    extra={"entity_type": spec.entity_type},
                                )
                                errors += 1
                                canonical_scan_complete = False
                                break
                            rows = list(result.scalars().unique().all())
                            for row in rows:
                                if not spec.include(row):
                                    continue
                                entity_id = str(row.id)
                                canonical_ids.add(entity_id)
                                try:
                                    payload = dict(spec.serializer(row))
                                    version = spec.version_reader(row)
                                    expected_checksum = self._cache.payload_checksum(payload)
                                    envelope = await self._cache.get_envelope(
                                        spec.entity_type, entity_id
                                    )
                                    compared += 1
                                    if (
                                        envelope is None
                                        or envelope.get("version") != version
                                        or envelope.get("checksum") != expected_checksum
                                    ):
                                        if await self._cache.set_json(
                                            spec.entity_type,
                                            entity_id,
                                            payload,
                                            version=version,
                                        ):
                                            repaired += 1
                                            RESYNC_MISMATCHES.labels(spec.entity_type).inc()
                                        else:
                                            errors += 1
                                except (TypeError, ValueError, AttributeError):
                                    logger.exception(
                                        "entity snapshot serialization failed",
                                        extra={
                                            "entity_type": spec.entity_type,
                                            "entity_id": entity_id,
                                        },
                                    )
                                    errors += 1
                            if len(rows) < self._batch_size:
                                break
                            offset += len(rows)

                        if not canonical_scan_complete:
                            # Never interpret an incomplete canonical view as
                            # proof that every secondary key is orphaned.
                            continue
                        secondary_ids = await self._cache.list_entity_ids(spec.entity_type)
                        for orphan_id in secondary_ids - canonical_ids:
                            if await self._cache.invalidate(spec.entity_type, orphan_id):
                                removed += 1
                            else:
                                errors += 1
            except SQLAlchemyError:
                logger.exception("state synchronization database session failed")
                errors += 1
        return StateSyncReport(
            compared=compared,
            repaired=repaired,
            removed=removed,
            errors=errors,
        )

    async def run_forever(self, stop_event: asyncio.Event | None = None) -> None:
        stop_event = stop_event or asyncio.Event()
        while not stop_event.is_set():
            try:
                await self.resynchronize_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("unexpected state synchronization failure")
            try:
                await asyncio.wait_for(
                    stop_event.wait(), timeout=self._interval_seconds
                )
            except TimeoutError:
                pass
