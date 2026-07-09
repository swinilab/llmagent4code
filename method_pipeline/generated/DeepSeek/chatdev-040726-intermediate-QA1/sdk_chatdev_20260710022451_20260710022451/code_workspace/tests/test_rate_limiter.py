"""
Tests for the token-bucket rate limiter.
"""

from __future__ import annotations

import pytest

from app.infrastructure.rate_limiter import TokenBucket


@pytest.mark.asyncio
async def test_token_bucket_consume() -> None:
    bucket = TokenBucket(max_tokens=10, refill_rate=100.0, refill_interval=0.01)
    # Consume all tokens
    for _ in range(10):
        assert await bucket.try_consume()
    # Bucket should be empty
    assert not await bucket.try_consume()


@pytest.mark.asyncio
async def test_token_bucket_refill() -> None:
    bucket = TokenBucket(max_tokens=10, refill_rate=1000.0, refill_interval=0.01)
    # Drain
    for _ in range(10):
        await bucket.try_consume()
    assert not await bucket.try_consume()
    # Wait for refill
    import asyncio
    await asyncio.sleep(0.05)
    # Should have tokens again
    assert await bucket.try_consume()
