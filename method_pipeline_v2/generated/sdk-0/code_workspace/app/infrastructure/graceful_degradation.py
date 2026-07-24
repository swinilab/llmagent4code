"""
Graceful degradation manager.
Implements NFR 2.1 (Graceful Degradation) by monitoring system resources
and disabling non-essential features under load.
Cross-platform resource monitoring with multiple fallback strategies.
"""
from __future__ import annotations

import asyncio
import logging
import os
import platform
import time
from dataclasses import dataclass, field

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class DegradationState:
    """Current degradation state of the system."""
    degraded: bool = False
    product_search_disabled: bool = False
    order_history_disabled: bool = False
    invoice_listing_disabled: bool = False
    reason: str = ""
    since: float = 0.0


class GracefulDegradationManager:
    """
    Monitors resource usage and disables non-essential features
    when memory or CPU thresholds are exceeded.
    Core checkout flow is always preserved.
    Uses multiple strategies for cross-platform compatibility.
    """

    def __init__(self) -> None:
        self._state = DegradationState()
        self._memory_threshold_mb = settings.degradation_memory_threshold_mb
        self._cpu_threshold = settings.degradation_cpu_threshold_percent
        self._running = False
        self._monitor_task: asyncio.Task[None] | None = None
        self._system = platform.system().lower()

    @property
    def state(self) -> DegradationState:
        return self._state

    async def start(self) -> None:
        """Start the resource monitor loop."""
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info(
            "GracefulDegradationManager started (mem=%dMB, cpu=%.1f%%, system=%s)",
            self._memory_threshold_mb,
            self._cpu_threshold,
            self._system,
        )

    async def stop(self) -> None:
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("GracefulDegradationManager stopped")

    async def _monitor_loop(self) -> None:
        while self._running:
            try:
                await self._check_resources()
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Resource monitor error")

    async def _check_resources(self) -> None:
        """Check memory and CPU usage and update degradation state."""
        memory_mb = self._get_memory_usage_mb()
        cpu_percent = self._get_cpu_percent()

        should_degrade = (
            memory_mb > self._memory_threshold_mb
            or cpu_percent > self._cpu_threshold
        )

        if should_degrade and not self._state.degraded:
            reasons = []
            if memory_mb > self._memory_threshold_mb:
                reasons.append(f"memory={memory_mb:.0f}MB > {self._memory_threshold_mb}MB")
            if cpu_percent > self._cpu_threshold:
                reasons.append(f"cpu={cpu_percent:.1f}% > {self._cpu_threshold}%")
            self._state = DegradationState(
                degraded=True,
                product_search_disabled=True,
                order_history_disabled=True,
                invoice_listing_disabled=True,
                reason="; ".join(reasons),
                since=time.monotonic(),
            )
            logger.warning("Degradation ENABLED: %s", self._state.reason)

        elif not should_degrade and self._state.degraded:
            self._state = DegradationState()
            logger.info("Degradation DISABLED — resources normal")

    def _get_memory_usage_mb(self) -> float:
        """Return approximate RSS memory usage in MB (cross-platform)."""
        # Strategy 1: Linux /proc/self/status
        if self._system == "linux":
            try:
                with open("/proc/self/status") as f:
                    for line in f:
                        if line.startswith("VmRSS:"):
                            parts = line.split()
                            return float(parts[1]) / 1024.0  # kB → MB
            except (FileNotFoundError, OSError, IndexError, ValueError):
                pass

        # Strategy 2: macOS psutil-like via vmmap or ps
        if self._system == "darwin":
            try:
                import subprocess
                result = subprocess.run(
                    ["ps", "-o", "rss=", "-p", str(os.getpid())],
                    capture_output=True, text=True, timeout=2,
                )
                if result.returncode == 0 and result.stdout.strip():
                    rss_kb = float(result.stdout.strip())
                    return rss_kb / 1024.0
            except (FileNotFoundError, OSError, subprocess.TimeoutExpired, ValueError):
                pass

        # Strategy 3: psutil if available
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / (1024 * 1024)
        except (ImportError, OSError, AttributeError):
            pass

        # Fallback: return 0 (no degradation triggered by memory alone)
        return 0.0

    def _get_cpu_percent(self) -> float:
        """Return approximate CPU usage as a percentage (cross-platform)."""
        # Strategy 1: Linux load average
        if self._system == "linux":
            try:
                load1, _load5, _load15 = os.getloadavg()
                cpu_count = os.cpu_count() or 1
                return (load1 / cpu_count) * 100.0
            except OSError:
                pass

        # Strategy 2: psutil if available
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except (ImportError, OSError, AttributeError):
            pass

        # Fallback: return 0
        return 0.0
