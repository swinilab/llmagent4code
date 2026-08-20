import asyncio
import time
from decimal import Decimal
from uuid import uuid4

import pytest
from redis.exceptions import RedisError
from sqlalchemy import func, select

from app.core.resilience import DependencyTimeoutError, run_with_timeout
from app.db.models import OutboxEventModel, ProductModel
from app.domain.mappers import serialize_product_snapshot
from app.infrastructure.cache import EntityCache
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from app.repositories.outbox_repository import OutboxRepository
from app.services.health_service import HealthService
from app.workers.outbox import OutboxDispatcher
from app.workers.state_sync import EntitySyncSpec, StateSynchronizer


class BrokenRedis:
    async def get(self, *_args, **_kwargs):
        raise RedisError("offline")

    async def set(self, *_args, **_kwargs):
        raise RedisError("offline")

    async def delete(self, *_args, **_kwargs):
        raise RedisError("offline")

    async def scan(self, *_args, **_kwargs):
        raise RedisError("offline")

    async def ping(self):
        raise RedisError("offline")


class RecordingRedis:
    def __init__(self) -> None:
        self.timestamps: list[float] = []

    async def xadd(self, *_args, **_kwargs) -> str:
        self.timestamps.append(time.monotonic())
        return "1-0"


class ReconciliationCache:
    def __init__(self) -> None:
        self.envelopes: dict[tuple[str, str], dict] = {}

    @staticmethod
    def payload_checksum(payload: dict) -> str:
        return EntityCache.payload_checksum(payload)

    async def get_envelope(self, entity_type: str, entity_id: str):
        return self.envelopes.get((entity_type, str(entity_id)))

    async def set_json(self, entity_type: str, entity_id: str, payload: dict, *, version=None):
        self.envelopes[(entity_type, str(entity_id))] = {
            "version": version,
            "checksum": self.payload_checksum(payload),
            "payload": payload,
        }
        return True

    async def list_entity_ids(self, entity_type: str):
        return {entity_id for kind, entity_id in self.envelopes if kind == entity_type}

    async def invalidate(self, entity_type: str, entity_id: str):
        self.envelopes.pop((entity_type, str(entity_id)), None)
        return True


async def test_timeout_is_detected() -> None:
    with pytest.raises(DependencyTimeoutError):
        await run_with_timeout(asyncio.sleep(0.05), 0.001, dependency="test dependency")


async def test_cache_and_health_degrade_when_redis_is_down(session_factory) -> None:
    broken = BrokenRedis()
    cache = EntityCache(broken, ttl_seconds=60, timeout_seconds=0.1)  # type: ignore[arg-type]
    assert await cache.get_json("product", uuid4()) is None
    assert not await cache.set_json("product", uuid4(), {"id": str(uuid4())}, version=1)
    report = await HealthService(session_factory, broken, timeout_seconds=0.1).check()  # type: ignore[arg-type]
    assert report["status"] == "degraded"
    assert report["criticalReady"] is True
    assert report["dependencies"] == {"postgresql": "up", "redis": "down"}


async def test_transaction_rolls_back_domain_and_outbox_together(session_factory) -> None:
    unit_of_work = SqlAlchemyUnitOfWork(session_factory)
    with pytest.raises(RuntimeError, match="forced rollback"):
        async with unit_of_work.transaction() as session:
            product = ProductModel(
                id=uuid4(),
                description="Rollback Product",
                price_amount=Decimal("10.00"),
                price_currency="USD",
                version=1,
            )
            session.add(product)
            OutboxRepository(session).add(
                aggregate_type="product",
                aggregate_id=product.id,
                event_type="product.created",
                payload={"productId": str(product.id)},
            )
            raise RuntimeError("forced rollback")
    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(ProductModel)) == 0
        assert await session.scalar(select(func.count()).select_from(OutboxEventModel)) == 0


async def test_outbox_dispatch_obeys_configured_maximum_rate(session_factory) -> None:
    async with session_factory() as session:
        async with session.begin():
            repository = OutboxRepository(session)
            for _ in range(4):
                repository.add(
                    aggregate_type="product",
                    aggregate_id=uuid4(),
                    event_type="product.created",
                    payload={},
                )
    redis = RecordingRedis()
    dispatcher = OutboxDispatcher(
        session_factory,
        redis,  # type: ignore[arg-type]
        stream_name="test-events",
        max_rate=2,
        batch_size=4,
        poll_interval_seconds=0.01,
        dependency_timeout_seconds=0.2,
    )
    assert await dispatcher.dispatch_pending_events() == 4
    assert len(redis.timestamps) == 4
    assert redis.timestamps[-1] - redis.timestamps[0] >= 0.9


async def test_state_resynchronization_repairs_corrupt_secondary_copy(session_factory) -> None:
    product = ProductModel(
        id=uuid4(),
        description="Synchronized Product",
        price_amount=Decimal("10.00"),
        price_currency="USD",
        version=3,
    )
    async with session_factory() as session:
        async with session.begin():
            session.add(product)
    cache = ReconciliationCache()
    cache.envelopes[("product", str(product.id))] = {
        "version": 2,
        "checksum": "corrupt",
        "payload": {"id": str(product.id)},
    }
    synchronizer = StateSynchronizer(
        session_factory,
        cache,  # type: ignore[arg-type]
        (EntitySyncSpec("product", ProductModel, serialize_product_snapshot),),
        interval_seconds=60,
        dependency_timeout_seconds=1,
    )
    report = await synchronizer.resynchronize_once()
    assert report.compared == 1
    assert report.repaired == 1
    envelope = cache.envelopes[("product", str(product.id))]
    assert envelope["version"] == 3
    assert envelope["checksum"] == cache.payload_checksum(envelope["payload"])
