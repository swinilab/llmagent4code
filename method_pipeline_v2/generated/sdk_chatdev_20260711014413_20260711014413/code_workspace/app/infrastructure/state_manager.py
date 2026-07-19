"""
State manager — preserves and restores operational state after crashes.
Implements NFR 2.3 (State Preservation).
Persists heartbeat to the database for true crash detection across restarts.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, select, Text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base, async_session_factory
from app.models.enums import OrderStatus
from app.repositories.order_repo import OrderRepository

logger = logging.getLogger(__name__)


class HeartbeatRecord(Base):
    """Persistent heartbeat record for crash detection."""
    __tablename__ = "heartbeats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(String(64), nullable=False, default="default")
    last_heartbeat = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(32), nullable=False, default="running")


class StateManager:
    """
    On startup, scans for orders in non-terminal states and logs them for recovery.
    Periodically persists a heartbeat to the database to detect crashes.
    """

    def __init__(self) -> None:
        self._running = False
        self._monitor_task: asyncio.Task[None] | None = None
        self._last_heartbeat: datetime | None = None
        self._instance_id: str = "default"

    @property
    def last_heartbeat(self) -> datetime | None:
        return self._last_heartbeat

    async def start(self) -> None:
        """Restore state on startup and begin heartbeat monitoring."""
        self._running = True
        await self._detect_crash()
        await self._restore_pending_orders()
        self._monitor_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("StateManager started")

    async def stop(self) -> None:
        self._running = False
        # Write a final heartbeat before stopping
        await self._write_heartbeat(status="shutdown")
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("StateManager stopped")

    async def _detect_crash(self) -> None:
        """Detect if the previous instance crashed by checking heartbeat status."""
        async with async_session_factory() as session:
            stmt = (
                select(HeartbeatRecord)
                .where(HeartbeatRecord.instance_id == self._instance_id)
                .order_by(HeartbeatRecord.last_heartbeat.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            last_record = result.scalar_one_or_none()
            if last_record and last_record.status == "running":
                logger.warning(
                    "Previous instance appears to have crashed! "
                    "Last heartbeat: %s",
                    last_record.last_heartbeat.isoformat(),
                )
            await session.commit()

    async def _restore_pending_orders(self) -> None:
        """Find orders that were in-flight when the system last stopped."""
        async with async_session_factory() as session:
            repo = OrderRepository(session)
            pending = await repo.list_pending_processing()
            if pending:
                logger.info(
                    "State recovery: found %d orders pending processing",
                    len(pending),
                )
                for order in pending:
                    logger.info(
                        "  Order %s [%s] — customer=%s, total=%.2f %s",
                        order.id,
                        order.status.value,
                        order.customer_id,
                        order.total_amount,
                        order.currency,
                    )
            else:
                logger.info("State recovery: no pending orders found")
            await session.commit()

    async def _heartbeat_loop(self) -> None:
        """Periodically record a heartbeat timestamp in the database."""
        while self._running:
            await self._write_heartbeat(status="running")
            await asyncio.sleep(5)

    async def _write_heartbeat(self, status: str = "running") -> None:
        """Write a heartbeat record to the database."""
        try:
            async with async_session_factory() as session:
                now = datetime.now(timezone.utc)
                record = HeartbeatRecord(
                    instance_id=self._instance_id,
                    last_heartbeat=now,
                    status=status,
                )
                session.add(record)
                await session.commit()
                self._last_heartbeat = now
        except Exception:
            logger.exception("Failed to write heartbeat")
