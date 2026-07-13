import time
import psutil
from typing import Callable, Set
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from starlette.responses import JSONResponse


class LoadSheddingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to shed load under high resource utilization.
    Monitors average request latency and system CPU usage.
    If overloaded, returns 503 for non-essential endpoints.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        essential_paths: Set[str] = None,
        window_size: int = 100,
        latency_threshold: float = 1.0,  # seconds
        cpu_threshold: float = 80.0,     # percent
    ):
        super().__init__(app)
        # Essential API prefixes (trailing slash optional)
        self.essential_paths = essential_paths or {
            "/api/v1/orders",
            "/api/v1/payments",
            "/api/v1/invoices",
            "/health",
        }
        self.window_size = window_size
        self.latency_threshold = latency_threshold
        self.cpu_threshold = cpu_threshold
        self.latencies = []  # rolling window of latencies
        self._overloaded = False

    def _update_metrics(self, process_time: float):
        self.latencies.append(process_time)
        if len(self.latencies) > self.window_size:
            self.latencies.pop(0)
        # Determine if overloaded based on average latency and CPU usage
        avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0
        cpu_usage = psutil.cpu_percent(interval=0.0)  # non-blocking
        overloaded = (
            avg_latency > self.latency_threshold or cpu_usage > self.cpu_threshold
        )
        self._overloaded = overloaded
        return overloaded

    def _is_essential_path(self, path: str) -> bool:
        # Check if path starts with any essential prefix
        for prefix in self.essential_paths:
            if path.startswith(prefix):
                return True
        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check overload before processing
        if self._overloaded and not self._is_essential_path(request.url.path):
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "Service temporarily unavailable due to high load"},
            )

        start_time = time.time()
        try:
            response: Response = await call_next(request)
            return response
        finally:
            process_time = time.time() - start_time
            self._update_metrics(process_time)