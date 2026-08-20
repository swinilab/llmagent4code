from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import TypeVar


T = TypeVar("T")


class DependencyTimeoutError(TimeoutError):
    """Raised when an infrastructure dependency exceeds its response budget."""

    def __init__(self, dependency: str, timeout_seconds: float) -> None:
        self.dependency = dependency
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"{dependency} did not respond within {timeout_seconds:g} seconds"
        )


async def run_with_timeout(
    operation: Awaitable[T],
    timeout_seconds: float,
    *,
    dependency: str = "dependency",
) -> T:
    """Await an infrastructure operation within a strict, observable deadline.

    ``asyncio.wait_for`` cancels the pending operation on expiry, preventing a
    slow dependency from consuming request or worker capacity indefinitely.
    Callers decide whether the detected timeout should fail the operation or
    activate a degraded fallback.
    """

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero")
    try:
        return await asyncio.wait_for(operation, timeout=timeout_seconds)
    except TimeoutError as exc:
        raise DependencyTimeoutError(dependency, timeout_seconds) from exc

