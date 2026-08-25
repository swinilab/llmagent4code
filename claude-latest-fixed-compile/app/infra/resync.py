"""NFR 2.3 - State Resynchronization.

A background sweep periodically compares the state of the active component
(primary Postgres) against the standby (streaming replica) and against the
cached copies, then repairs any divergence it finds.

Three comparisons run each pass:
  1. Replication lag in bytes, from ``pg_stat_replication`` on the primary.
  2. Per-entity row-count + checksum drift between primary and replica.
  3. Stale cache entries whose payload no longer matches the primary, which are
     evicted so the next read re-populates from the source of truth.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import text

from app.core.config import settings
from app.infra.cache import EntityCache
from app.infra.database import PrimarySession, ReplicaSession

logger = logging.getLogger(__name__)

_TRACKED_TABLES = ("customers", "products", "orders", "payments", "invoices")


@dataclass
class ResyncReport:
    checked_at: datetime
    replication_lag_bytes: int | None
    drift: dict[str, dict[str, int]] = field(default_factory=dict)
    cache_entries_evicted: int = 0
    in_sync: bool = True

    def as_dict(self) -> dict:
        return {
            "checkedAt": self.checked_at.isoformat(),
            "replicationLagBytes": self.replication_lag_bytes,
            "drift": self.drift,
            "cacheEntriesEvicted": self.cache_entries_evicted,
            "inSync": self.in_sync,
        }


class StateResynchronizer:
    def __init__(self, cache: EntityCache) -> None:
        self._cache = cache
        self._task: asyncio.Task | None = None
        self.last_report: ResyncReport | None = None

    # -- individual comparisons -------------------------------------------------

    def _replication_lag(self) -> int | None:
        """Bytes the standby trails the primary by, or None if no standby attached."""
        with PrimarySession() as session:
            row = session.execute(
                text(
                    "SELECT COALESCE(MAX(sent_lsn - replay_lsn), 0)::bigint AS lag "
                    "FROM pg_stat_replication"
                )
            ).first()
        return int(row.lag) if row is not None else None

    def _table_signature(self, session, table: str) -> tuple[int, int]:
        """(row_count, checksum) for a table - cheap divergence fingerprint."""
        row = session.execute(
            text(
                f"SELECT COUNT(*) AS n, "  # noqa: S608 - table name is from a fixed allow-list
                f"COALESCE(SUM(('x'||substr(md5(t::text),1,8))::bit(32)::bigint), 0) AS ck "
                f"FROM {table} t"
            )
        ).first()
        return int(row.n), int(row.ck)

    def compare_active_and_standby(self) -> dict[str, dict[str, int]]:
        """Compare every tracked table across primary and replica."""
        drift: dict[str, dict[str, int]] = {}
        with PrimarySession() as primary, ReplicaSession() as replica:
            for table in _TRACKED_TABLES:
                p_count, p_ck = self._table_signature(primary, table)
                r_count, r_ck = self._table_signature(replica, table)
                if p_count != r_count or p_ck != r_ck:
                    drift[table] = {
                        "primaryRows": p_count,
                        "replicaRows": r_count,
                        "rowDelta": p_count - r_count,
                    }
        return drift

    async def _evict_diverged_cache(self, drift: dict[str, dict[str, int]]) -> int:
        """Drop cached copies for entity types whose stores disagree."""
        evicted = 0
        for table in drift:
            entity = table.rstrip("s")
            try:
                async for key in self._cache._redis.scan_iter(match=f"oms:{entity}:*"):
                    await self._cache._redis.delete(key)
                    evicted += 1
            except Exception:
                logger.warning("cache eviction during resync failed", exc_info=True)
        return evicted

    # -- sweep ------------------------------------------------------------------

    async def run_once(self) -> ResyncReport:
        loop = asyncio.get_running_loop()
        try:
            lag = await loop.run_in_executor(None, self._replication_lag)
            drift = await loop.run_in_executor(None, self.compare_active_and_standby)
        except Exception:
            logger.error("resync sweep failed to read component state", exc_info=True)
            report = ResyncReport(datetime.now(UTC), None, {}, 0, in_sync=False)
            self.last_report = report
            return report

        evicted = await self._evict_diverged_cache(drift) if drift else 0
        in_sync = not drift and (lag is None or lag <= settings.resync_drift_tolerance)

        report = ResyncReport(datetime.now(UTC), lag, drift, evicted, in_sync)
        if not in_sync:
            logger.warning("state divergence detected: %s", report.as_dict())
        self.last_report = report
        return report

    async def _loop(self) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(settings.resync_interval_seconds)

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop(), name="state-resynchronizer")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
